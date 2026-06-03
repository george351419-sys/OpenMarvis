"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Clock, Trash2 } from "lucide-react";

import { api, ScheduleDTO } from "@/lib/api";

function triggerLabel(s: ScheduleDTO): string {
  switch (s.trigger_type) {
    case "once":
      return `单次 · ${s.trigger_spec}`;
    case "interval":
      return `每 ${s.trigger_spec}s`;
    case "cron":
      return `cron · ${s.trigger_spec}`;
    default:
      return s.trigger_spec;
  }
}

export default function SchedulesPage() {
  const [rows, setRows] = useState<ScheduleDTO[] | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function refresh() {
    try {
      setRows(await api.listSchedules());
      setError(null);
    } catch (e) {
      setError(String(e));
    }
  }

  useEffect(() => { refresh(); }, []);

  async function cancel(id: string) {
    if (!confirm(`确认取消任务 ${id}？`)) return;
    setBusyId(id);
    try {
      await api.cancelSchedule(id);
      setRows((s) => s?.filter((r) => r.id !== id) ?? null);
    } catch (e) {
      setError(String(e));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <Link href="/" className="text-sm text-muted-foreground hover:underline
                                    inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" /> 返回
        </Link>
        <h1 className="text-lg font-semibold inline-flex items-center gap-2">
          <Clock className="w-4 h-4" /> 定时任务
        </h1>
        <button className="text-xs hover:underline" onClick={refresh}>刷新</button>
      </div>

      {error && (
        <div className="mb-3 text-sm text-red-600 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {rows === null ? (
        <div className="text-sm text-muted-foreground">加载中…</div>
      ) : rows.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed
                          border-border rounded p-6 text-center">
          还没有定时任务。让 Marvis 创建一个：「每天 9 点告诉我天气」。
        </div>
      ) : (
        <ul className="space-y-2">
          {rows.map((r) => (
            <li key={r.id} className="border border-border rounded p-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="text-sm font-medium truncate">
                    {r.description || "(未命名)"}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    {triggerLabel(r)}
                  </div>
                  <div className="text-xs mt-1 line-clamp-2">{r.instruction}</div>
                  {r.next_run_at && (
                    <div className="text-xs text-muted-foreground mt-1">
                      下次：{r.next_run_at}
                    </div>
                  )}
                  <Link href={`/c/${r.origin_conv_id}`}
                        className="text-xs text-blue-600 hover:underline mt-1
                                    inline-block">
                    来源会话 →
                  </Link>
                </div>
                <button
                  className="text-xs text-red-600 hover:bg-red-50 rounded p-1
                              disabled:opacity-50"
                  onClick={() => cancel(r.id)}
                  disabled={busyId === r.id}
                  title="取消"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
