"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { Bell, Check } from "lucide-react";

import { api, NotificationDTO } from "@/lib/api";

const POLL_MS = 30_000;

export function NotificationBell() {
  const [items, setItems] = useState<NotificationDTO[]>([]);
  const [open, setOpen] = useState(false);
  const popRef = useRef<HTMLDivElement | null>(null);

  async function refresh() {
    try {
      setItems(await api.listUnreadNotifications());
    } catch {
      // network failure — keep prior state, retry on next tick
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, POLL_MS);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (!popRef.current) return;
      if (!popRef.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  async function markRead(id: number) {
    await api.markNotificationRead(id);
    setItems((s) => s.filter((n) => n.id !== id));
  }

  const count = items.length;

  return (
    <div className="relative" ref={popRef}>
      <button
        type="button"
        className="relative p-1.5 rounded hover:bg-muted/60"
        onClick={() => setOpen((v) => !v)}
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
        <div className="absolute right-0 top-full mt-1 w-80 max-h-96 overflow-y-auto
                          rounded border border-border bg-background shadow-lg z-50">
          <div className="px-3 py-2 border-b border-border text-xs text-muted-foreground">
            未读通知 {count > 0 ? `(${count})` : ""}
          </div>
          {count === 0 ? (
            <div className="px-3 py-6 text-center text-xs text-muted-foreground">
              暂无未读通知
            </div>
          ) : (
            <ul>
              {items.map((n) => (
                <li key={n.id} className="border-b border-border last:border-0">
                  <div className="px-3 py-2 flex items-start gap-2">
                    <Link
                      href={`/c/${n.virtual_conv_id}`}
                      className="flex-1 min-w-0"
                      onClick={() => { markRead(n.id); setOpen(false); }}
                    >
                      <div className="flex items-center gap-1 text-xs">
                        <span
                          className={`inline-block w-1.5 h-1.5 rounded-full
                                        ${n.status === "success" ? "bg-green-500" : "bg-red-500"}`}
                        />
                        <span className="text-muted-foreground">
                          {new Date(n.created_at * 1000).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-sm mt-0.5 line-clamp-2">{n.summary || "(无摘要)"}</div>
                    </Link>
                    <button
                      type="button"
                      className="p-1 rounded hover:bg-muted/60"
                      title="标为已读"
                      onClick={() => markRead(n.id)}
                    >
                      <Check className="w-3 h-3" />
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
