"""文件全文索引（SQLite FTS5）。

FTS5 给我们带:
- 关键词搜索（path / name / content 三字段独立 token 化）
- BM25 默认排序
- 中文友好的 trigram tokenizer（不需要分词器依赖）

每个 conv 共享一个索引（按 conv_id 列过滤）；增量索引按 mtime 判断是否过期。
内容字段对超过 _MAX_CONTENT_BYTES 的文件只索引前几 KB，避免索引爆炸。
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import text

from ..tools.read_file import _PARSERS  # 复用文件解析器
from .db import create_engine  # noqa: F401  仅类型/避免循环

_MAX_CONTENT_BYTES = 256 * 1024  # 单文件最多索引前 256KB 内容
_TEXT_EXTS = frozenset({
    ".md", ".markdown", ".txt", ".log", ".json", ".yaml", ".yml",
    ".pdf", ".docx", ".pptx", ".xlsx", ".xlsm", ".csv",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".sh",
})


@dataclass
class FileIndexHit:
    path: str
    name: str
    snippet: str
    score: float        # BM25：越小越相关；这里取负让"越大越好"


def init_file_index(engine) -> None:
    """创建 FTS5 虚拟表 + 元数据表。幂等。"""
    with engine.connect() as conn:
        # FTS5 虚拟表存 conv_id / path / name / content（trigram，中英都行）
        conn.execute(text(
            "CREATE VIRTUAL TABLE IF NOT EXISTS file_index_fts "
            "USING fts5(conv_id, path, name, content, "
            "tokenize='trigram', prefix='2 3')"
        ))
        # 元数据表：path 唯一，记 mtime/size，用于判断增量
        conn.execute(text(
            "CREATE TABLE IF NOT EXISTS file_index_meta ("
            "conv_id TEXT NOT NULL, "
            "path TEXT NOT NULL, "
            "mtime REAL NOT NULL, "
            "size INTEGER NOT NULL, "
            "indexed_at INTEGER NOT NULL, "
            "PRIMARY KEY (conv_id, path))"
        ))
        conn.commit()


def _read_content(p: Path) -> str:
    """尽力读取文件文本内容。不支持的扩展名返回空串（仍索引 path/name）。"""
    ext = p.suffix.lower()
    if ext not in _TEXT_EXTS:
        return ""
    parser = _PARSERS.get(ext)
    try:
        if parser is None:
            # 兜底：纯文本读
            raw = p.read_text(encoding="utf-8", errors="replace")
        else:
            # parser 第二参数是 args（带 sheet 等），这里只走默认
            class _Empty:
                sheet_name: str | None = None
                sheet_index: int | None = None
                read_all_sheets: bool = False
            raw = parser(p, _Empty())
    except Exception:  # noqa: BLE001
        return ""
    return raw[:_MAX_CONTENT_BYTES]


def index_path(engine, *, conv_id: str, path: Path) -> bool:
    """索引单个文件。返回是否真的入库（True=新增/更新，False=已最新）。"""
    if not path.exists() or not path.is_file():
        return False
    st = path.stat()
    mtime, size = st.st_mtime, st.st_size
    with engine.connect() as conn:
        row = conn.execute(text(
            "SELECT mtime, size FROM file_index_meta "
            "WHERE conv_id=:c AND path=:p"
        ), {"c": conv_id, "p": str(path)}).fetchone()
        if row is not None and row[0] == mtime and row[1] == size:
            return False  # 已是最新
        content = _read_content(path)
        # 先删旧，再插新；FTS5 没有 UPSERT
        conn.execute(text(
            "DELETE FROM file_index_fts WHERE conv_id=:c AND path=:p"
        ), {"c": conv_id, "p": str(path)})
        conn.execute(text(
            "INSERT INTO file_index_fts(conv_id, path, name, content) "
            "VALUES (:c, :p, :n, :ct)"
        ), {"c": conv_id, "p": str(path), "n": path.name, "ct": content})
        conn.execute(text(
            "INSERT OR REPLACE INTO file_index_meta "
            "(conv_id, path, mtime, size, indexed_at) "
            "VALUES (:c, :p, :m, :s, :t)"
        ), {"c": conv_id, "p": str(path), "m": mtime, "s": size,
              "t": int(time.time())})
        conn.commit()
        return True


def index_directory(engine, *, conv_id: str, root: Path,
                     follow_symlinks: bool = False) -> dict[str, int]:
    """递归索引一个目录。返回 {indexed: N, skipped: M}。"""
    indexed = 0
    skipped = 0
    for p in root.rglob("*"):
        if p.is_symlink() and not follow_symlinks:
            continue
        if not p.is_file():
            continue
        if index_path(engine, conv_id=conv_id, path=p):
            indexed += 1
        else:
            skipped += 1
    return {"indexed": indexed, "skipped": skipped}


def search(engine, *, conv_id: str, query: str,
            field: str = "content", limit: int = 20) -> list[FileIndexHit]:
    """FTS5 查询。field: content / name / path / any。"""
    if not query.strip():
        return []
    # FTS5 的 MATCH 语法：'field: query' 限定字段；不带前缀则搜全部字段
    if field == "any":
        match_expr = query
    elif field in ("content", "name", "path"):
        # 转义单引号；FTS 查询语法不能含未配对的特殊字符
        safe = query.replace('"', '""')
        match_expr = f'{field}:"{safe}"'
    else:
        raise ValueError(f"未知 field: {field}")
    sql = text(
        "SELECT path, name, "
        "snippet(file_index_fts, 3, '<b>', '</b>', '...', 32) AS snip, "
        "bm25(file_index_fts) AS score "
        "FROM file_index_fts "
        "WHERE conv_id=:c AND file_index_fts MATCH :q "
        "ORDER BY score LIMIT :lim"
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"c": conv_id, "q": match_expr,
                                    "lim": limit}).fetchall()
    return [
        FileIndexHit(path=r[0], name=r[1], snippet=r[2] or "",
                      score=-float(r[3]))  # BM25 越小越好；取负让大=好
        for r in rows
    ]


def prune_missing(engine, *, conv_id: str) -> int:
    """清理已不存在的索引条目。返回清理数。"""
    removed = 0
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT path FROM file_index_meta WHERE conv_id=:c"
        ), {"c": conv_id}).fetchall()
        for (p,) in rows:
            if not Path(p).exists():
                conn.execute(text(
                    "DELETE FROM file_index_fts WHERE conv_id=:c AND path=:p"
                ), {"c": conv_id, "p": p})
                conn.execute(text(
                    "DELETE FROM file_index_meta WHERE conv_id=:c AND path=:p"
                ), {"c": conv_id, "p": p})
                removed += 1
        conn.commit()
    return removed


def stats(engine, *, conv_id: str) -> dict[str, Any]:
    with engine.connect() as conn:
        n = conn.execute(text(
            "SELECT COUNT(*) FROM file_index_meta WHERE conv_id=:c"
        ), {"c": conv_id}).scalar() or 0
    return {"file_count": int(n)}
