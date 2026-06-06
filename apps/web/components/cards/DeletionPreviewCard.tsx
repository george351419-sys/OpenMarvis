"use client";

import { useState } from "react";

import { api } from "@/lib/api";

interface Props {
  convId: string;
  ask_id: string;
  files: string[];
}

export function DeletionPreviewCard({ convId, ask_id, files }: Props) {
  const [checked, setChecked] = useState<Set<string>>(new Set(files));
  const [done, setDone] = useState(false);

  const toggle = (f: string) =>
    setChecked((s) => {
      const n = new Set(s);
      n.has(f) ? n.delete(f) : n.add(f);
      return n;
    });

  const confirm = async () => {
    if (!ask_id) return;
    await api.answerAsk(convId, ask_id, [...checked]);
    setDone(true);
  };

  const cancel = async () => {
    if (!ask_id) return;
    await api.answerAsk(convId, ask_id, ["cancel"]);
    setDone(true);
  };

  if (done) {
    return (
      <div className="rounded-md border border-border p-3 my-3 bg-muted/30">
        <div className="text-xs text-muted-foreground">删除请求已处理</div>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-red-500/40 p-4 my-3 bg-red-500/5">
      <div className="text-sm font-medium text-red-700 dark:text-red-400 mb-3">
        以下文件将被移入回收站（7 天后永久删除）
      </div>
      <ul className="space-y-1.5 mb-4">
        {files.map((f) => (
          <li key={f} className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={checked.has(f)}
              onChange={() => toggle(f)}
              className="accent-red-600 cursor-pointer"
            />
            <span className="font-mono text-xs text-muted-foreground break-all">{f}</span>
          </li>
        ))}
      </ul>
      {ask_id && (
        <div className="flex gap-2">
          <button
            onClick={confirm}
            disabled={checked.size === 0}
            className="px-3 py-1 text-sm rounded bg-red-600 text-white hover:bg-red-700 disabled:opacity-40">
            确认删除 ({checked.size} 项)
          </button>
          <button
            onClick={cancel}
            className="px-3 py-1 text-sm rounded border border-border hover:bg-muted">
            取消
          </button>
        </div>
      )}
    </div>
  );
}
