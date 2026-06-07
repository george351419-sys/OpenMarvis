"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, ExternalLink, Pencil, Plus, RefreshCw, Trash2, X } from "lucide-react";

import { api, ScheduleDTO } from "@/lib/api";
import { ConversationSidebar } from "@/components/ConversationSidebar";

// ─── helpers ──────────────────────────────────────────────────────────────────

type TriggerType = "once" | "daily" | "weekly" | "interval" | "cron";

function triggerLabel(s: ScheduleDTO): string {
  switch (s.trigger_type) {
    case "once":     return `单次 · ${s.trigger_spec}`;
    case "interval": return `每 ${s.trigger_spec} 秒`;
    case "cron":     return `定时 · ${s.trigger_spec}`;
    default:         return s.trigger_spec;
  }
}

function nextRunLabel(s: ScheduleDTO): string | null {
  if (!s.next_run_at) return null;
  try {
    const d = new Date(s.next_run_at);
    return d.toLocaleString("zh-CN", { month: "short", day: "numeric",
                                        hour: "2-digit", minute: "2-digit" });
  } catch {
    return s.next_run_at;
  }
}

// ─── New-task drawer ───────────────────────────────────────────────────────────

const TRIGGER_OPTIONS: { value: TriggerType; label: string; hint: string }[] = [
  { value: "daily",    label: "每天",   hint: "选择每天几点执行" },
  { value: "weekly",   label: "每周",   hint: "选择星期几 + 时间" },
  { value: "once",     label: "单次",   hint: "选择具体日期时间" },
  { value: "interval", label: "间隔",   hint: "每隔多少分钟重复" },
  { value: "cron",     label: "Cron",   hint: "高级：cron 表达式" },
];

const WEEK_DAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"];

function buildInstruction(desc: string, type: TriggerType,
                           time: string, weekday: string,
                           date: string, interval: string, cron: string): string {
  switch (type) {
    case "daily":    return `每天 ${time} ${desc}`;
    case "weekly":   return `每${weekday} ${time} ${desc}`;
    case "once":     return `${date} ${time} ${desc}`;
    case "interval": return `每 ${interval} 分钟 ${desc}`;
    case "cron":     return `定时 (${cron}) ${desc}`;
  }
}

function NewTaskDrawer({
  onClose,
  onCreated,
  editTarget,
}: {
  onClose: () => void;
  onCreated: () => void;
  editTarget?: ScheduleDTO;
}) {
  const initType = (editTarget?.trigger_type as TriggerType) ?? "daily";
  const initInterval = editTarget?.trigger_type === "interval"
    ? String(Math.round(parseInt(editTarget.trigger_spec) / 60) || 60)
    : "60";
  const initCron = editTarget?.trigger_type === "cron" ? editTarget.trigger_spec : "0 9 * * *";

  const [desc, setDesc]         = useState(editTarget?.description ?? "");
  const [type, setType]         = useState<TriggerType>(initType);
  const [time, setTime]         = useState("09:00");
  const [weekday, setWeekday]   = useState("周一");
  const [date, setDate]         = useState(() => new Date().toISOString().slice(0, 10));
  const [interval, setInterval] = useState(initInterval);
  const [cron, setCron]         = useState(initCron);
  const [loading, setLoading]   = useState(false);
  const [err, setErr]           = useState<string | null>(null);

  const isEditing = !!editTarget;

  async function submit() {
    if (!desc.trim()) { setErr("请填写任务描述"); return; }
    setLoading(true);
    setErr(null);
    try {
      if (isEditing) {
        await api.cancelSchedule(editTarget!.id);
      }
      const instruction = buildInstruction(desc.trim(), type, time, weekday, date, interval, cron);
      const conv = await api.createConversation("自动任务");
      sessionStorage.setItem(`chat_prefill_${conv.id}`, `帮我创建一个定时任务：${instruction}`);
      window.location.href = `/c/${conv.id}`;
    } catch (e: any) {
      setErr(e?.message ?? "操作失败，请稍后重试");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center">
      <div className="absolute inset-0 bg-black/30 backdrop-blur-sm" onClick={onClose} />
      <div className="relative bg-background rounded-t-2xl sm:rounded-2xl shadow-2xl w-full max-w-md p-6 mx-0 sm:mx-4">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-base font-bold">{isEditing ? "编辑自动任务" : "新建自动任务"}</h2>
          <button onClick={onClose} className="p-1 rounded hover:bg-muted transition">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="space-y-4">
          {/* Description */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
              任务描述
            </label>
            <input
              value={desc}
              onChange={(e) => setDesc(e.target.value)}
              placeholder="例如：提醒我喝水、汇总今日新闻"
              className="w-full h-10 px-3 text-sm border border-border rounded-xl focus:outline-none focus:ring-2 focus:ring-ring bg-background"
            />
          </div>

          {/* Trigger type */}
          <div>
            <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
              执行频率
            </label>
            <div className="grid grid-cols-5 gap-1.5">
              {TRIGGER_OPTIONS.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => setType(opt.value)}
                  className={`py-2 rounded-lg text-xs font-medium border transition
                    ${type === opt.value
                      ? "bg-foreground text-background border-foreground"
                      : "border-border hover:bg-muted"}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Conditional time fields */}
          {(type === "daily" || type === "weekly" || type === "once") && (
            <div className="flex gap-3">
              {type === "weekly" && (
                <div className="flex-1">
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">星期</label>
                  <select
                    value={weekday}
                    onChange={(e) => setWeekday(e.target.value)}
                    className="w-full h-10 px-3 text-sm border border-border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-ring"
                  >
                    {WEEK_DAYS.map((d) => <option key={d}>{d}</option>)}
                  </select>
                </div>
              )}
              {type === "once" && (
                <div className="flex-1">
                  <label className="text-xs font-medium text-muted-foreground mb-1.5 block">日期</label>
                  <input type="date" value={date} onChange={(e) => setDate(e.target.value)}
                    className="w-full h-10 px-3 text-sm border border-border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-ring" />
                </div>
              )}
              <div className={type === "daily" ? "w-full" : "flex-1"}>
                <label className="text-xs font-medium text-muted-foreground mb-1.5 block">时间</label>
                <input type="time" value={time} onChange={(e) => setTime(e.target.value)}
                  className="w-full h-10 px-3 text-sm border border-border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-ring" />
              </div>
            </div>
          )}

          {type === "interval" && (
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                间隔（分钟）
              </label>
              <input
                type="number" min="1" value={interval}
                onChange={(e) => setInterval(e.target.value)}
                className="w-full h-10 px-3 text-sm border border-border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-ring"
              />
            </div>
          )}

          {type === "cron" && (
            <div>
              <label className="text-xs font-medium text-muted-foreground mb-1.5 block">
                Cron 表达式
              </label>
              <input
                value={cron} onChange={(e) => setCron(e.target.value)}
                placeholder="0 9 * * *"
                className="w-full h-10 px-3 text-sm border border-border rounded-xl bg-background focus:outline-none focus:ring-2 focus:ring-ring font-mono"
              />
              <p className="text-[11px] text-muted-foreground mt-1">
                格式：分 时 日 月 周
              </p>
            </div>
          )}

          {err && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
              {err}
            </p>
          )}

          <button
            onClick={submit}
            disabled={loading}
            className="w-full h-11 bg-foreground text-background rounded-xl text-sm font-semibold hover:opacity-90 transition disabled:opacity-50"
          >
            {loading ? (isEditing ? "保存中…" : "创建中…") : (isEditing ? "保存修改" : "创建任务")}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Task card ────────────────────────────────────────────────────────────────

function TaskCard({ row, onCancel, onEdit }: { row: ScheduleDTO; onCancel: () => void; onEdit: () => void }) {
  const [busy, setBusy] = useState(false);
  const next = nextRunLabel(row);

  async function cancel() {
    if (!confirm("确认取消此任务？")) return;
    setBusy(true);
    try {
      await api.cancelSchedule(row.id);
      onCancel();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="border border-border rounded-xl p-4 bg-background hover:border-foreground/20 transition">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold truncate">{row.description || "(未命名)"}</p>
          <p className="text-xs text-muted-foreground mt-0.5">{triggerLabel(row)}</p>
          {row.instruction && (
            <p className="text-xs text-muted-foreground/70 mt-1 line-clamp-1">{row.instruction}</p>
          )}
          <div className="flex items-center gap-3 mt-2">
            {next && (
              <span className="text-[11px] text-muted-foreground bg-muted px-2 py-0.5 rounded-full">
                下次 {next}
              </span>
            )}
            <Link
              href={`/c/${row.origin_conv_id}`}
              className="text-[11px] text-blue-600 hover:underline inline-flex items-center gap-1"
            >
              来源会话 <ExternalLink className="w-2.5 h-2.5" />
            </Link>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <button
            onClick={onEdit}
            className="p-2 rounded-lg hover:bg-muted text-muted-foreground transition"
            title="编辑任务"
          >
            <Pencil className="w-4 h-4" />
          </button>
          <button
            onClick={cancel}
            disabled={busy}
            className="p-2 rounded-lg hover:bg-red-50 hover:text-red-600 text-muted-foreground transition disabled:opacity-40"
            title="取消任务"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function SchedulesPage() {
  const [rows, setRows]         = useState<ScheduleDTO[] | null>(null);
  const [error, setError]       = useState<string | null>(null);
  const [showNew, setShowNew]   = useState(false);
  const [editTarget, setEditTarget] = useState<ScheduleDTO | undefined>();
  const [refreshing, setRefreshing] = useState(false);

  async function refresh() {
    setRefreshing(true);
    try {
      setRows(await api.listSchedules());
      setError(null);
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
    }
  }

  useEffect(() => { refresh(); }, []);

  return (
    <div className="flex h-screen">
      <ConversationSidebar />
      <main className="flex-1 min-w-0 overflow-y-auto bg-muted/20">
        <div className="max-w-2xl mx-auto px-6 py-8">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="w-9 h-9 rounded-xl bg-foreground flex items-center justify-center">
                <Clock className="w-4 h-4 text-background" />
              </div>
              <div>
                <h1 className="text-lg font-bold">自动任务</h1>
                <p className="text-xs text-muted-foreground">定时让 AI 帮你完成重复工作</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <button
                onClick={refresh}
                disabled={refreshing}
                className="p-2 rounded-lg hover:bg-muted transition text-muted-foreground disabled:opacity-40"
                title="刷新"
              >
                <RefreshCw className={`w-4 h-4 ${refreshing ? "animate-spin" : ""}`} />
              </button>
              <button
                onClick={() => setShowNew(true)}
                className="inline-flex items-center gap-1.5 h-9 px-4 bg-foreground text-background rounded-xl text-sm font-medium hover:opacity-90 transition"
              >
                <Plus className="w-4 h-4" /> 新建任务
              </button>
            </div>
          </div>

          {error && (
            <div className="mb-4 text-sm text-red-600 border border-red-200 rounded-xl px-4 py-3 bg-red-50">
              {error}
            </div>
          )}

          {rows === null && !error && (
            <div className="py-12 text-center text-sm text-muted-foreground">加载中…</div>
          )}

          {rows?.length === 0 && (
            <div className="border border-dashed border-border rounded-2xl p-12 text-center">
              <Clock className="w-10 h-10 text-muted-foreground/25 mx-auto mb-4" />
              <p className="text-sm font-medium text-muted-foreground mb-1">还没有自动任务</p>
              <p className="text-xs text-muted-foreground/60 mb-4">
                点击「新建任务」通过表单设置，<br />或直接在对话中告诉 AI（如「每天 9 点提醒我开会」）
              </p>
              <button
                onClick={() => setShowNew(true)}
                className="inline-flex items-center gap-1.5 h-9 px-5 bg-foreground text-background rounded-xl text-sm font-medium hover:opacity-90 transition"
              >
                <Plus className="w-4 h-4" /> 新建任务
              </button>
            </div>
          )}

          {rows && rows.length > 0 && (
            <div className="space-y-3">
              {rows.map((r) => (
                <TaskCard
                  key={r.id}
                  row={r}
                  onCancel={() => setRows((s) => s?.filter((x) => x.id !== r.id) ?? null)}
                  onEdit={() => { setEditTarget(r); setShowNew(true); }}
                />
              ))}
            </div>
          )}
        </div>
      </main>

      {showNew && (
        <NewTaskDrawer
          onClose={() => { setShowNew(false); setEditTarget(undefined); }}
          onCreated={() => { refresh(); }}
          editTarget={editTarget}
        />
      )}
    </div>
  );
}
