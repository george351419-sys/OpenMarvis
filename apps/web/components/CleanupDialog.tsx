"use client";
import { useState } from "react";
import { Sparkles, X } from "lucide-react";

import { api } from "@/lib/api";

interface Props {
  onClose: () => void;
  onPurged: () => void;
}

type DryRun = { dry_run: true; would_purge: number; sample_ids: string[] };
type Real = { dry_run: false; purged: number; by_table: Record<string, number> };

export function CleanupDialog({ onClose, onPurged }: Props) {
  const [emptyTitle, setEmptyTitle] = useState(true);
  const [maxMessages, setMaxMessages] = useState<number>(0);
  const [minAgeDays, setMinAgeDays] = useState<number>(0);
  const [preview, setPreview] = useState<DryRun | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const filter = () => ({
    empty_title: emptyTitle,
    max_messages: maxMessages,
    min_age_days: minAgeDays,
  });

  const runPreview = async () => {
    setBusy(true); setError(null);
    try {
      const r = await api.cleanupConversations({ ...filter(), dry_run: true });
      setPreview(r as DryRun);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally { setBusy(false); }
  };

  const runReal = async () => {
    if (!preview || preview.would_purge === 0) return;
    if (!window.confirm(
      `即将永久删除 ${preview.would_purge} 个会话及其所有数据。\n` +
      `此操作不可恢复。确认继续？`,
    )) return;
    setBusy(true); setError(null);
    try {
      const r = await api.cleanupConversations({ ...filter(), dry_run: false });
      const real = r as Real;
      alert(`已清理 ${real.purged} 个会话`);
      onPurged();
      onClose();
    } catch (e: any) {
      setError(e?.message ?? String(e));
    } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
         onClick={onClose}>
      <div className="bg-background border border-border rounded-lg shadow-xl
                       p-5 w-[480px] max-w-[90vw]"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Sparkles className="w-4 h-4" /> 批量清理空会话
          </h2>
          <button onClick={onClose} className="p-1 hover:bg-muted rounded">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-3 text-sm">
          <label className="flex items-center gap-2">
            <input type="checkbox" checked={emptyTitle}
                   onChange={(e) => setEmptyTitle(e.target.checked)} />
            仅清理标题为空 / 单字符（&quot;t&quot;、&quot;&quot;）的会话
          </label>

          <label className="flex items-center gap-2">
            最大消息数 ≤
            <input type="number" min={-1} max={10}
                   value={maxMessages}
                   onChange={(e) => setMaxMessages(parseInt(e.target.value || "0"))}
                   className="w-16 border border-border rounded px-1.5 py-0.5" />
            <span className="text-muted-foreground text-xs">（-1 = 不限）</span>
          </label>

          <label className="flex items-center gap-2">
            仅超过
            <input type="number" min={0} max={365}
                   value={minAgeDays}
                   onChange={(e) => setMinAgeDays(parseInt(e.target.value || "0"))}
                   className="w-16 border border-border rounded px-1.5 py-0.5" />
            天的会话
          </label>
        </div>

        {error && (
          <div className="mt-3 text-sm text-red-600 border border-red-300
                            bg-red-50 rounded p-2">
            {error}
          </div>
        )}

        {preview && (
          <div className="mt-3 text-sm border border-border rounded p-3 bg-muted/40">
            <div className="font-medium mb-1">
              将清理 <span className="text-red-600">{preview.would_purge}</span> 个会话
            </div>
            {preview.sample_ids.length > 0 && (
              <div className="text-xs text-muted-foreground font-mono">
                示例: {preview.sample_ids.slice(0, 5).join(", ")}
                {preview.sample_ids.length < preview.would_purge && " ..."}
              </div>
            )}
          </div>
        )}

        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose}
                  className="px-3 py-1 text-sm border border-border rounded
                              hover:bg-muted">
            取消
          </button>
          <button onClick={runPreview} disabled={busy}
                  className="px-3 py-1 text-sm border border-border rounded
                              hover:bg-muted disabled:opacity-50">
            {busy ? "..." : "预览"}
          </button>
          <button onClick={runReal}
                  disabled={busy || !preview || preview.would_purge === 0}
                  className="px-3 py-1 text-sm bg-red-600 text-white rounded
                              hover:bg-red-700 disabled:opacity-50">
            确认清理
          </button>
        </div>
      </div>
    </div>
  );
}
