"use client";

import { useEffect, useState } from "react";

import { useFilePreview } from "@/lib/stores/filePreview";

const TEXT_EXTS = new Set([
  "txt","md","markdown","json","yaml","yml","toml","csv","xml","html","htm",
  "css","js","ts","tsx","jsx","py","sh","bash","zsh","env","log","ini","conf",
]);
const IMAGE_EXTS = new Set(["png","jpg","jpeg","gif","webp","svg","heic","heif","bmp"]);
const PDF_EXT = "pdf";
// Office formats rendered via macOS Quick Look on the backend → returned as PNG
const QL_EXTS = new Set(["pptx","ppt","key","docx","doc","pages","xlsx","xls","numbers","epub"]);
const BINARY_EXTS = new Set([
  "zip","tar","gz","7z","mp4","mov","avi","mp3","wav","exe","dmg","pkg",
]);

function fmtSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function fileIcon(ext: string): string {
  if (IMAGE_EXTS.has(ext)) return "🖼";
  if (ext === PDF_EXT) return "📄";
  if (["pptx","ppt"].includes(ext)) return "📊";
  if (["xlsx","xls"].includes(ext)) return "📊";
  if (["docx","doc"].includes(ext)) return "📝";
  if (["md","markdown"].includes(ext)) return "📝";
  if (["zip","tar","gz","7z"].includes(ext)) return "🗜";
  if (["mp4","mov","avi"].includes(ext)) return "🎬";
  if (["mp3","wav"].includes(ext)) return "🎵";
  return "📄";
}

export function FilePreviewPanel() {
  const { path, close } = useFilePreview();
  const [content, setContent] = useState<string | null>(null);
  const [size, setSize] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [qlLoading, setQlLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const ext = (path?.split(".").pop() ?? "").toLowerCase();
  // path is already decoded in the store; display name is always readable
  const fileName = decodeURIComponent(path?.split("/").pop() ?? "");
  const isImage = IMAGE_EXTS.has(ext);
  const isPdf = ext === PDF_EXT;
  const isQl = QL_EXTS.has(ext);   // Office files — backend converts via qlmanage → PNG
  const isBinary = BINARY_EXTS.has(ext);

  const previewUrl = path
    ? `/api/proxy/files/preview?path=${encodeURIComponent(path)}`
    : "";

  useEffect(() => {
    if (!path) { setContent(null); setSize(null); setError(null); setQlLoading(false); return; }
    setLoading(true);
    setQlLoading(false);
    setContent(null);
    setSize(null);
    setError(null);

    if (isBinary) {
      fetch(`/api/proxy/files/meta?path=${encodeURIComponent(path)}`)
        .then((r) => r.ok ? r.json() : Promise.reject(r.status))
        .then((d) => setSize(d.size))
        .catch(() => {})
        .finally(() => setLoading(false));
      return;
    }

    if (isPdf || isQl) {
      // PDF → iframe loads itself; Office → qlmanage can take 5-20s, track separately
      if (isQl) setQlLoading(true);
      fetch(`/api/proxy/files/meta?path=${encodeURIComponent(path)}`)
        .then((r) => r.ok ? r.json() : null)
        .then((d) => d && setSize(d.size))
        .catch(() => {})
        .finally(() => setLoading(false));
      return;
    }

    fetch(previewUrl)
      .then(async (r) => {
        if (!r.ok) throw new Error(`${r.status}`);
        const cl = r.headers.get("content-length");
        if (cl) setSize(Number(cl));
        if (isImage) return null;
        return r.text();
      })
      .then((t) => setContent(t ?? ""))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [path]);

  const openFile = () =>
    fetch(`/api/proxy/files/open?path=${encodeURIComponent(path!)}`, { method: "POST" });
  const revealFile = () =>
    fetch(`/api/proxy/files/reveal?path=${encodeURIComponent(path!)}`, { method: "POST" });

  if (!path) return null;

  return (
    <div className="flex flex-col border-l border-border bg-background w-[420px] shrink-0 h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="text-sm font-medium truncate">{fileName}</span>
        <button
          onClick={close}
          className="ml-2 shrink-0 px-2 py-1 text-xs rounded hover:bg-muted transition"
        >
          ✕
        </button>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-auto relative">
        {loading && (
          <div className="flex items-center justify-center h-40 text-sm text-muted-foreground">
            加载中…
          </div>
        )}
        {!loading && error && (
          <div className="p-4 text-sm text-red-600">无法加载：{error}</div>
        )}
        {!loading && !error && isImage && (
          <img src={previewUrl} alt={fileName} className="max-w-full" />
        )}
        {!loading && !error && isPdf && (
          <iframe
            src={previewUrl}
            className="w-full h-full border-0"
            title={fileName}
          />
        )}
        {/* Office files: backend runs qlmanage (5-20s) and returns a PNG */}
        {!loading && !error && isQl && qlLoading && (
          <div className="flex flex-col items-center justify-center h-40 gap-2 text-muted-foreground">
            <span className="text-sm">正在生成预览，请稍候…</span>
            <span className="text-xs opacity-60">Office 文件预览可能需要几秒钟</span>
          </div>
        )}
        {!loading && !error && isQl && (
          <img
            src={previewUrl}
            alt={fileName}
            className="max-w-full object-contain"
            style={{ display: qlLoading ? "none" : "block" }}
            onLoad={() => setQlLoading(false)}
            onError={() => {
              setQlLoading(false);
              setError("预览生成失败，请点击「打开」使用原生应用查看");
            }}
          />
        )}
        {!loading && !error && isBinary && (
          <div className="flex flex-col items-center justify-center h-40 gap-3 text-muted-foreground">
            <span className="text-5xl">{fileIcon(ext)}</span>
            <span className="text-sm">无法在此预览此文件类型</span>
          </div>
        )}
        {!loading && !error && content !== null && !isImage && !isPdf && !isBinary && (
          <pre className="p-4 text-xs font-mono whitespace-pre-wrap break-all leading-relaxed">
            {content}
          </pre>
        )}
      </div>

      {/* Footer */}
      <div className="px-4 py-3 border-t border-border space-y-2">
        <div className="flex items-center justify-between text-[11px] text-muted-foreground">
          <span className="uppercase tracking-wide">{ext || "文件"}</span>
          {size !== null && <span>{fmtSize(size)}</span>}
        </div>
        <div className="text-[11px] text-muted-foreground break-all leading-tight">{path}</div>
        <div className="flex gap-2 pt-1">
          <button
            onClick={openFile}
            className="flex-1 py-1.5 text-xs rounded border border-border hover:bg-muted transition"
          >
            打开
          </button>
          <button
            onClick={revealFile}
            className="flex-1 py-1.5 text-xs rounded border border-border hover:bg-muted transition"
          >
            所在位置
          </button>
        </div>
      </div>
    </div>
  );
}
