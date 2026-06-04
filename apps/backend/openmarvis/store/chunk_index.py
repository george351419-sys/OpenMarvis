"""文件 chunk 级 FTS5 索引。

file_index 索引整文件、返回"哪个文件命中"；
chunk_index 把每个文件切成 ~300 词的 chunk 单独索引，返回"哪段命中"，
适合在长 PDF / 长文档里精准定位。

Chunker 策略：
- 按段落（空行分隔）合并相邻段落，目标 chunk_size_chars=1200，硬上限 2000
- 段落超长 → 按句号 / 行号继续切
- chunk_idx 从 0 起，可用于 "请定位到 N 段" 后续工具调用
"""
from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text

from ..tools.read_file import _PARSERS

_TARGET_CHARS = 1200
_HARD_CAP = 2000
_TEXT_EXTS = frozenset({
    ".md", ".markdown", ".txt", ".log",
    ".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".csv",
})
_MAX_FILE_BYTES = 50 * 1024 * 1024


@dataclass
class ChunkHit:
    file_path: str
    chunk_idx: int
    chunk_text: str       # 命中的完整 chunk 原文
    snippet: str          # FTS5 高亮片段
    score: float          # BM25 取负，越大越好


def init_chunk_index(engine) -> None:
    """创建 FTS5 chunk 表 + meta 表。幂等。"""
    with engine.connect() as conn:
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_index_fts "
            "USING fts5(conv_id, file_path, chunk_idx UNINDEXED, content, "
            "tokenize='trigram', prefix='2 3')"
        ))
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS chunk_index_meta ("
            "conv_id TEXT NOT NULL, "
            "file_path TEXT NOT NULL, "
            "mtime REAL NOT NULL, "
            "size INTEGER NOT NULL, "
            "num_chunks INTEGER NOT NULL, "
            "indexed_at INTEGER NOT NULL, "
            "PRIMARY KEY (conv_id, file_path))"
        ))
        conn.commit()


# ---------------- Chunker ----------------


_PARA_RE = re.compile(r"\n\s*\n+")
_SENT_RE = re.compile(r"(?<=[。！？.!?])\s+")


def chunk_text(raw: str, *, target_chars: int = _TARGET_CHARS,
                hard_cap: int = _HARD_CAP) -> list[str]:
    """段落→句→行的 3 级切分；返回 chunks。"""
    if not raw.strip():
        return []
    paragraphs = [p.strip() for p in _PARA_RE.split(raw) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paragraphs:
        if len(p) > hard_cap:
            # 段落太大 → 按句切，再不行按行切
            for piece in _split_oversized(p, target_chars, hard_cap):
                if buf and len(buf) + len(piece) + 2 > target_chars:
                    chunks.append(buf)
                    buf = piece
                else:
                    buf = piece if not buf else f"{buf}\n\n{piece}"
            continue
        if buf and len(buf) + len(p) + 2 > target_chars:
            chunks.append(buf)
            buf = p
        else:
            buf = p if not buf else f"{buf}\n\n{p}"
    if buf:
        chunks.append(buf)
    return chunks


def _split_oversized(p: str, target: int, cap: int) -> list[str]:
    """长段落：先按句切；句子还太长就按 cap 强切。"""
    sentences = _SENT_RE.split(p)
    out: list[str] = []
    buf = ""
    for s in sentences:
        s = s.strip()
        if not s:
            continue
        if len(s) > cap:
            # 句子也太长 → 直接按 cap 切
            if buf:
                out.append(buf)
                buf = ""
            for i in range(0, len(s), cap):
                out.append(s[i:i + cap])
            continue
        if buf and len(buf) + len(s) + 1 > target:
            out.append(buf)
            buf = s
        else:
            buf = s if not buf else f"{buf} {s}"
    if buf:
        out.append(buf)
    return out


# ---------------- 内容提取（复用 read_file 解析器） ----------------


def _extract_text(p: Path) -> str:
    ext = p.suffix.lower()
    if ext not in _TEXT_EXTS:
        return ""
    parser = _PARSERS.get(ext)
    try:
        if parser is None:
            return p.read_text(encoding="utf-8", errors="replace")

        class _Empty:
            sheet_name: str | None = None
            sheet_index: int | None = None
            read_all_sheets: bool = False

        return parser(p, _Empty())
    except Exception:  # noqa: BLE001
        return ""


# ---------------- 索引 ----------------


def index_path_chunks(engine, *, conv_id: str, path: Path) -> int | None:
    """索引单文件的 chunks。返回 chunk 数；None=跳过（未变化）；0=空。"""
    if not path.exists() or not path.is_file():
        return None
    st = path.stat()
    if st.st_size > _MAX_FILE_BYTES:
        return None
    mtime, size = st.st_mtime, st.st_size
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT mtime, size FROM chunk_index_meta "
            "WHERE conv_id=:c AND file_path=:p"
        ), {"c": conv_id, "p": str(path)}).fetchone()
        if row is not None and row[0] == mtime and row[1] == size:
            return None  # 跳过
        raw = _extract_text(path)
        chunks = chunk_text(raw) if raw else []
        # 删旧 chunks（mtime 变化时 chunk 边界可能完全错位）
        conn.execute(text(
            "DELETE FROM chunk_index_fts WHERE conv_id=:c AND file_path=:p"
        ), {"c": conv_id, "p": str(path)})
        for idx, ch in enumerate(chunks):
            conn.execute(text(
                "INSERT INTO chunk_index_fts(conv_id, file_path, chunk_idx, content) "
                "VALUES (:c, :p, :i, :ct)"
            ), {"c": conv_id, "p": str(path), "i": idx, "ct": ch})
        conn.execute(text(
            "INSERT OR REPLACE INTO chunk_index_meta "
            "(conv_id, file_path, mtime, size, num_chunks, indexed_at) "
            "VALUES (:c, :p, :m, :s, :n, :t)"
        ), {"c": conv_id, "p": str(path), "m": mtime, "s": size,
              "n": len(chunks), "t": int(time.time())})
        conn.commit()
        return len(chunks)


def index_directory_chunks(engine, *, conv_id: str, root: Path) -> dict[str, int]:
    """递归索引目录。返回 {files: N, chunks: M, skipped: K}。"""
    files = 0
    chunks = 0
    skipped = 0
    for p in root.rglob("*"):
        if p.is_symlink() or not p.is_file():
            continue
        n = index_path_chunks(engine, conv_id=conv_id, path=p)
        if n is None:
            skipped += 1
            continue
        files += 1
        chunks += n
    return {"files": files, "chunks": chunks, "skipped": skipped}


def search_chunks(engine, *, conv_id: str, query: str,
                    limit: int = 10) -> list[ChunkHit]:
    """FTS5 chunk 查询。返回原 chunk 全文 + snippet 高亮。"""
    if not query.strip():
        return []
    safe = query.replace('"', '""')
    match_expr = f'content:"{safe}"'
    sql = text(
        "SELECT file_path, chunk_idx, content, "
        "snippet(chunk_index_fts, 3, '<b>', '</b>', '...', 32) AS snip, "
        "bm25(chunk_index_fts) AS score "
        "FROM chunk_index_fts "
        "WHERE conv_id=:c AND chunk_index_fts MATCH :q "
        "ORDER BY score LIMIT :lim"
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"c": conv_id, "q": match_expr,
                                    "lim": limit}).fetchall()
    return [
        ChunkHit(file_path=r[0], chunk_idx=int(r[1]),
                  chunk_text=r[2] or "", snippet=r[3] or "",
                  score=-float(r[4]))
        for r in rows
    ]


def chunk_stats(engine, *, conv_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        files = conn.execute(text(
            "SELECT COUNT(*) FROM chunk_index_meta WHERE conv_id=:c"
        ), {"c": conv_id}).scalar() or 0
        chunks = conn.execute(text(
            "SELECT SUM(num_chunks) FROM chunk_index_meta WHERE conv_id=:c"
        ), {"c": conv_id}).scalar() or 0
    return {"files": int(files), "chunks": int(chunks)}
