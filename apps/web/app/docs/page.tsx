"use client";
import { useEffect, useRef, useState } from "react";
import {
  FileText,
  Folder,
  FolderOpen,
  Plus,
  RefreshCw,
  Sparkles,
  Tag,
  Trash2,
  X,
} from "lucide-react";

import { api } from "@/lib/api";
import { ConversationSidebar } from "@/components/ConversationSidebar";

const STORAGE_KEY = "om_doc_roots";

function loadRoots(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function saveRoots(roots: string[]) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(roots));
}

// ─── Add-directory modal ───────────────────────────────────────────────────────

function AddDirModal({ onAdd, onClose }: { onAdd: (p: string) => void; onClose: () => void }) {
  const [path, setPath] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const common = [
    "~/Desktop",
    "~/Documents",
    "~/Downloads",
    "~/Pictures",
  ];

  function submit() {
    const p = path.trim();
    if (!p) return;
    onAdd(p);
    onClose();
  }

  function handleFolderPick(e: React.ChangeEvent<HTMLInputElement>) {
    const files = e.target.files;
    if (!files || files.length === 0) return;
    const first = files[0].webkitRelativePath || files[0].name;
    const folderName = first.split("/")[0];
    // Extract folder path: use webkitRelativePath prefix up to first "/"
    // The absolute path is unavailable in browsers for security; use the folder name
    // as a placeholder that the user can complete, or use the common location hint
    setPath(`~/${folderName}`);
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-background rounded-t-2xl sm:rounded-2xl shadow-2xl w-full max-w-md p-6 mx-0 sm:mx-4">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-bold">授权目录</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition">
            <X className="w-4 h-4" />
          </button>
        </div>
        <p className="text-xs text-muted-foreground mb-4 leading-relaxed">
          授权后，OpenMarvis 可以读取该目录下的文档，并提供自动归类、搜索和分析能力。
        </p>
        <label className="text-xs font-medium text-muted-foreground mb-1.5 block">目录路径</label>
        <div className="flex gap-2 mb-3">
          <input
            value={path}
            onChange={(e) => setPath(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && submit()}
            placeholder="/Users/你的名字/Documents"
            className="flex-1 h-10 px-3 text-sm border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-ring bg-background font-mono"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="h-10 px-3 text-sm border border-border rounded-xl hover:bg-muted transition text-muted-foreground whitespace-nowrap"
          >
            浏览…
          </button>
          {/* Hidden folder picker — browser security only gives folder name, not full path */}
          <input
            ref={fileInputRef}
            type="file"
            // @ts-ignore — webkitdirectory is non-standard but widely supported
            webkitdirectory=""
            className="hidden"
            onChange={handleFolderPick}
          />
        </div>
        <div className="flex flex-wrap gap-1.5 mb-4">
          {common.map((p) => (
            <button
              key={p}
              onClick={() => setPath(p)}
              className="text-xs px-2.5 py-1 rounded-lg border border-border hover:bg-muted transition text-muted-foreground"
            >
              {p}
            </button>
          ))}
        </div>
        <button
          onClick={submit}
          className="w-full h-11 bg-foreground text-background rounded-xl text-sm font-semibold hover:opacity-90 transition"
        >
          授权并添加
        </button>
      </div>
    </div>
  );
}

// ─── Directory card ────────────────────────────────────────────────────────────

interface DirStats { files: number; types: Record<string, number> }

function DirCard({
  root,
  onRemove,
}: {
  root: string;
  onRemove: () => void;
}) {
  const [stats, setStats] = useState<DirStats | null>(null);
  const [loading, setLoading] = useState(true);
  const displayName = root.split("/").pop() || root;

  useEffect(() => {
    setLoading(true);
    fetch(`/api/proxy/files/meta?path=${encodeURIComponent(root)}`)
      .then((r) => r.ok ? r.json() : null)
      .then(() => {
        // Just confirm the directory exists; list to get rough stats
        return fetch(`/api/proxy/files/preview?path=${encodeURIComponent(root)}`);
      })
      .catch(() => {})
      .finally(() => {
        setStats({ files: 0, types: {} });
        setLoading(false);
      });
  }, [root]);

  async function organize() {
    const conv = await api.createConversation("文档整理");
    sessionStorage.setItem(`chat_prefill_${conv.id}`, `帮我整理这个目录，按文件类型自动分类：${root}`);
    window.location.href = `/c/${conv.id}`;
  }

  async function search() {
    const conv = await api.createConversation("文档搜索");
    sessionStorage.setItem(`chat_prefill_${conv.id}`, `帮我在这个目录里搜索文档：${root}`);
    window.location.href = `/c/${conv.id}`;
  }

  return (
    <div className="border border-border rounded-2xl overflow-hidden bg-background hover:border-foreground/20 transition">
      {/* Card header */}
      <div className="px-4 py-3.5 flex items-center gap-3 border-b border-border/60 bg-muted/20">
        <FolderOpen className="w-5 h-5 text-amber-500 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold truncate">{displayName}</p>
          <p className="text-[11px] text-muted-foreground font-mono truncate">{root}</p>
        </div>
        <button
          onClick={onRemove}
          className="p-1.5 rounded-lg hover:bg-red-50 hover:text-red-500 text-muted-foreground transition"
          title="移除授权"
        >
          <Trash2 className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Actions */}
      <div className="px-4 py-3 flex gap-2">
        <button
          onClick={organize}
          className="flex-1 flex items-center justify-center gap-1.5 h-8 text-xs font-medium border border-border rounded-lg hover:bg-muted transition"
        >
          <Tag className="w-3.5 h-3.5" /> 自动归类
        </button>
        <button
          onClick={search}
          className="flex-1 flex items-center justify-center gap-1.5 h-8 text-xs font-medium border border-border rounded-lg hover:bg-muted transition"
        >
          <Sparkles className="w-3.5 h-3.5" /> 智能搜索
        </button>
        <button
          onClick={() => {
            fetch(`/api/proxy/files/reveal?path=${encodeURIComponent(root)}`, { method: "POST" });
          }}
          className="flex-1 flex items-center justify-center gap-1.5 h-8 text-xs font-medium border border-border rounded-lg hover:bg-muted transition"
        >
          <Folder className="w-3.5 h-3.5" /> 打开目录
        </button>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DocsPage() {
  const [roots, setRoots]     = useState<string[]>([]);
  const [showAdd, setShowAdd] = useState(false);

  useEffect(() => {
    setRoots(loadRoots());
  }, []);

  function addRoot(p: string) {
    const next = [...new Set([...roots, p])];
    setRoots(next);
    saveRoots(next);
  }

  function removeRoot(p: string) {
    const next = roots.filter((r) => r !== p);
    setRoots(next);
    saveRoots(next);
  }

  return (
    <div className="flex h-screen">
      <ConversationSidebar />
      <main className="flex-1 min-w-0 overflow-y-auto bg-muted/20">
        <div className="max-w-2xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-foreground flex items-center justify-center">
                <FileText className="w-4 h-4 text-background" />
              </div>
              <div>
                <h1 className="text-lg font-bold">文档</h1>
                <p className="text-xs text-muted-foreground">授权目录后，AI 可自动归类和分析你的本地文档</p>
              </div>
            </div>
            <button
              onClick={() => setShowAdd(true)}
              className="inline-flex items-center gap-1.5 h-9 px-4 bg-foreground text-background rounded-xl text-sm font-medium hover:opacity-90 transition"
            >
              <Plus className="w-4 h-4" /> 添加目录
            </button>
          </div>

          {/* Permission notice */}
          <div className="mb-6 p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 leading-relaxed">
            <strong>权限说明：</strong>添加目录后，OpenMarvis 仅在你主动发起操作时读取该目录，不会在后台自动扫描或上传任何文件。你可以随时移除授权。
          </div>

          {roots.length === 0 ? (
            <div className="border border-dashed border-border rounded-2xl p-12 text-center">
              <FileText className="w-10 h-10 text-muted-foreground/25 mx-auto mb-4" />
              <p className="text-sm font-medium text-muted-foreground mb-1">还没有授权目录</p>
              <p className="text-xs text-muted-foreground/60 mb-4">
                添加目录后，可以让 AI 帮你智能归类、<br />搜索和分析本地文档
              </p>
              <button
                onClick={() => setShowAdd(true)}
                className="inline-flex items-center gap-1.5 h-9 px-5 bg-foreground text-background rounded-xl text-sm font-medium hover:opacity-90 transition"
              >
                <Plus className="w-4 h-4" /> 添加目录
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {roots.map((r) => (
                <DirCard key={r} root={r} onRemove={() => removeRoot(r)} />
              ))}

              {/* Quick actions hint */}
              <div className="mt-6 p-4 rounded-xl border border-dashed border-border text-center">
                <p className="text-xs text-muted-foreground">
                  也可以直接在对话中说：
                </p>
                <div className="flex flex-wrap justify-center gap-2 mt-2">
                  {[
                    "帮我整理 ~/Documents",
                    "找所有 2024 年的合同",
                    "分析桌面上的 Excel 文件",
                  ].map((eg) => (
                    <button
                      key={eg}
                      onClick={async () => {
                        const conv = await api.createConversation("");
                        sessionStorage.setItem(`chat_prefill_${conv.id}`, eg);
                        window.location.href = `/c/${conv.id}`;
                      }}
                      className="text-xs px-3 py-1.5 rounded-lg border border-border hover:bg-muted transition text-muted-foreground"
                    >
                      {eg}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </main>

      {showAdd && (
        <AddDirModal onAdd={addRoot} onClose={() => setShowAdd(false)} />
      )}
    </div>
  );
}
