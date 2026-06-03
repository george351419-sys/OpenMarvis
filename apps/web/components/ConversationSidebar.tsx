"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { Clock, Plus, Trash2 } from "lucide-react";

import { api, ConversationDTO } from "@/lib/api";
import { NotificationBell } from "./NotificationBell";

export function ConversationSidebar({ activeId }: { activeId?: string }) {
  const [convs, setConvs] = useState<ConversationDTO[]>([]);
  useEffect(() => { api.listConversations().then(setConvs).catch(() => {}); }, []);
  return (
    <aside className="w-64 border-r border-border h-screen flex flex-col">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <span className="text-sm font-semibold">会话</span>
        <div className="flex items-center gap-1">
          <Link href="/schedules" className="p-1.5 rounded hover:bg-muted/60"
                title="定时任务">
            <Clock className="w-4 h-4" />
          </Link>
          <NotificationBell />
          <button className="text-xs inline-flex items-center gap-1 hover:underline"
                  onClick={async () => {
                    const c = await api.createConversation("");
                    window.location.href = `/c/${c.id}`;
                  }}>
            <Plus className="w-3 h-3" /> 新建
          </button>
        </div>
      </div>
      <ul className="flex-1 overflow-y-auto">
        {convs.map((c) => (
          <li key={c.id}
              className={`group flex items-center justify-between px-3 py-2 text-sm
                          ${c.id === activeId ? "bg-muted" : "hover:bg-muted/60"}`}>
            <Link href={`/c/${c.id}`} className="flex-1 truncate">
              {c.title || "未命名"}
            </Link>
            <button className="opacity-0 group-hover:opacity-100"
                    onClick={async () => { await api.deleteConversation(c.id);
                                            setConvs((s) => s.filter((x) => x.id !== c.id)); }}>
              <Trash2 className="w-3 h-3 text-red-600" />
            </button>
          </li>
        ))}
      </ul>
    </aside>
  );
}
