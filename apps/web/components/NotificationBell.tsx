"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell, Check, ChevronRight, X } from "lucide-react";

import { api, NotificationDTO } from "@/lib/api";

const POLL_MS = 30_000;

export function NotificationBell() {
  const [items, setItems] = useState<NotificationDTO[]>([]);
  const [open, setOpen] = useState(false);
  const [selected, setSelected] = useState<NotificationDTO | null>(null);
  const [dropPos, setDropPos] = useState<{ top: number; left: number }>({ top: 0, left: 0 });
  const btnRef = useRef<HTMLButtonElement>(null);
  const popRef = useRef<HTMLDivElement | null>(null);

  async function refresh() {
    try { setItems(await api.listUnreadNotifications()); } catch {}
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!popRef.current) return;
      if (!popRef.current.contains(e.target as Node) &&
          !btnRef.current?.contains(e.target as Node)) {
        setOpen(false);
        setSelected(null);
      }
    }
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  function toggleOpen() {
    if (open) { setOpen(false); setSelected(null); return; }
    if (btnRef.current) {
      const rect = btnRef.current.getBoundingClientRect();
      // Anchor to bell's left edge; clamp so dropdown doesn't overflow viewport right
      const left = Math.min(rect.left, window.innerWidth - 320 - 8);
      setDropPos({ top: rect.bottom + 6, left });
    }
    setOpen(true);
  }

  async function markRead(id: number) {
    await api.markNotificationRead(id);
    setItems((s) => s.filter((n) => n.id !== id));
    setSelected((s) => (s?.id === id ? null : s));
  }

  async function markAllRead() {
    await Promise.all(items.map((n) => api.markNotificationRead(n.id)));
    setItems([]);
    setSelected(null);
  }

  const count = items.length;

  return (
    <div className="relative">
      <button
        ref={btnRef}
        type="button"
        className="relative p-1.5 rounded hover:bg-muted/60"
        onClick={toggleOpen}
        aria-label="通知"
      >
        <Bell className="w-4 h-4" />
        {count > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-[16px] px-1
                            rounded-full bg-red-600 text-white text-[10px]
                            leading-[16px] text-center">
            {count > 99 ? "99+" : count}
          </span>
        )}
      </button>

      {open && (
        <div
          ref={popRef}
          style={{ position: "fixed", top: dropPos.top, left: dropPos.left, zIndex: 9999 }}
          className="w-80 max-h-[480px] overflow-hidden flex flex-col
                     rounded-xl border border-border bg-background shadow-2xl"
        >
          {/* Header */}
          <div className="px-3 py-2.5 border-b border-border flex items-center justify-between gap-2">
            <span className="text-xs font-semibold text-muted-foreground shrink-0">
              未读通知{count > 0 ? ` (${count})` : ""}
            </span>
            <div className="flex items-center gap-1 ml-auto">
              {count > 0 && (
                <button onClick={markAllRead}
                        className="text-[11px] text-muted-foreground hover:text-foreground
                                   px-2 py-0.5 rounded hover:bg-muted/60 transition whitespace-nowrap">
                  全部已读
                </button>
              )}
              <button onClick={() => { setOpen(false); setSelected(null); }}
                      className="p-0.5 rounded hover:bg-muted/60">
                <X className="w-3.5 h-3.5 text-muted-foreground" />
              </button>
            </div>
          </div>

          {/* List or detail */}
          {selected ? (
            // ── Detail view ──
            <div className="flex-1 overflow-y-auto p-4">
              <button
                onClick={() => setSelected(null)}
                className="text-xs text-muted-foreground hover:text-foreground mb-3 flex items-center gap-1"
              >
                ← 返回列表
              </button>
              <div className="flex items-center gap-1.5 mb-2">
                <span className={`inline-block w-2 h-2 rounded-full shrink-0
                  ${selected.status === "success" ? "bg-green-500" : "bg-red-500"}`} />
                <span className="text-xs text-muted-foreground">
                  {new Date(selected.created_at * 1000).toLocaleString("zh-CN")}
                </span>
                <span className={`ml-auto text-[11px] px-2 py-0.5 rounded-full
                  ${selected.status === "success"
                    ? "bg-green-50 text-green-700 border border-green-200"
                    : "bg-red-50 text-red-700 border border-red-200"}`}>
                  {selected.status === "success" ? "成功" : "失败"}
                </span>
              </div>
              <p className="text-sm leading-relaxed mb-4 whitespace-pre-wrap">
                {selected.summary || "(无摘要)"}
              </p>
              <div className="flex gap-2">
                <Link
                  href={`/c/${selected.virtual_conv_id}`}
                  onClick={() => { markRead(selected.id); setOpen(false); setSelected(null); }}
                  className="flex-1 flex items-center justify-center gap-1.5 h-8 text-xs font-medium
                             border border-border rounded-lg hover:bg-muted transition"
                >
                  查看对话 <ChevronRight className="w-3 h-3" />
                </Link>
                <button
                  onClick={() => markRead(selected.id)}
                  className="h-8 px-3 text-xs border border-border rounded-lg hover:bg-muted transition
                             text-muted-foreground flex items-center gap-1"
                >
                  <Check className="w-3 h-3" /> 标已读
                </button>
              </div>
            </div>
          ) : (
            // ── List view ──
            <ul className="flex-1 overflow-y-auto divide-y divide-border">
              {count === 0 ? (
                <li className="px-3 py-8 text-center text-xs text-muted-foreground">
                  暂无未读通知
                </li>
              ) : (
                items.map((n) => (
                  <li key={n.id}
                      className="flex items-start gap-2 px-3 py-2.5 hover:bg-muted/40
                                 cursor-pointer transition"
                      onClick={() => setSelected(n)}>
                    <span className={`mt-1.5 inline-block w-1.5 h-1.5 rounded-full shrink-0
                      ${n.status === "success" ? "bg-green-500" : "bg-red-500"}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-[11px] text-muted-foreground">
                        {new Date(n.created_at * 1000).toLocaleString("zh-CN",
                          { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                      </p>
                      <p className="text-sm mt-0.5 line-clamp-2 leading-snug">
                        {n.summary || "(无摘要)"}
                      </p>
                    </div>
                    <div className="flex items-center gap-1 shrink-0">
                      <button
                        type="button"
                        className="p-1 rounded hover:bg-muted/80"
                        title="标为已读"
                        onClick={(e) => { e.stopPropagation(); markRead(n.id); }}
                      >
                        <Check className="w-3 h-3 text-muted-foreground" />
                      </button>
                    </div>
                  </li>
                ))
              )}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
