"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Clock, Download, FileText, MessagesSquare, Plus,
  Search, Trash2, Wrench,
} from "lucide-react";

import { api, ConversationDTO } from "@/lib/api";
import { CleanupDialog } from "./CleanupDialog";
import { NotificationBell } from "./NotificationBell";

const NAV_ITEMS = [
  { href: "/schedules", icon: Clock,     label: "自动任务" },
  { href: "/skills",    icon: Wrench,    label: "技能广场" },
  { href: "/docs",      icon: FileText,  label: "文档" },
  { href: "/download",  icon: Download,  label: "下载客户端" },
];

export function ConversationSidebar({ activeId }: { activeId?: string }) {
  const pathname = usePathname();
  const [convs, setConvs]           = useState<ConversationDTO[]>([]);
  const [search, setSearch]         = useState("");
  const [showCleanup, setShowCleanup] = useState(false);
  const [creating, setCreating]     = useState(false);
  const searchRef = useRef<HTMLInputElement>(null);

  const reload = useCallback(() => {
    api.listConversations().then(setConvs).catch(() => {});
  }, []);
  useEffect(() => { reload(); }, [reload]);

  const filtered = search.trim()
    ? convs.filter((c) => (c.title || "未命名").toLowerCase().includes(search.toLowerCase()))
    : convs;

  async function newConv() {
    if (creating) return;
    setCreating(true);
    try {
      const c = await api.createConversation("");
      window.location.href = `/c/${c.id}`;
    } finally {
      setCreating(false);
    }
  }

  return (
    <aside className="w-[220px] shrink-0 border-r border-border h-screen flex flex-col
                      bg-background select-none overflow-hidden">

      {/* Brand */}
      <div className="px-4 pt-5 pb-3 flex items-center justify-between">
        <Link href="/" className="text-[18px] font-bold tracking-tight hover:opacity-80 transition">
          OpenMarvis
        </Link>
        <NotificationBell />
      </div>

      {/* Search */}
      <div className="px-3 mb-2">
        <div className="relative">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5
                             text-muted-foreground/40 pointer-events-none" />
          <input
            ref={searchRef}
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索"
            className="w-full h-8 pl-8 pr-3 text-xs bg-muted/50 rounded-lg border border-transparent
                       focus:outline-none focus:ring-1 focus:ring-ring focus:bg-background
                       placeholder:text-muted-foreground/40 transition"
          />
        </div>
      </div>

      {/* New conversation button */}
      <div className="px-3 mb-3">
        <button
          onClick={newConv}
          disabled={creating}
          className="w-full flex items-center gap-2 px-3 py-2 rounded-lg border border-border
                     text-sm font-medium hover:bg-muted/60 transition text-left disabled:opacity-50"
        >
          <Plus className="w-3.5 h-3.5 text-muted-foreground" />
          新建对话
        </button>
      </div>

      {/* Feature nav */}
      <div className="px-3 mb-1">
        <p className="text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest
                      px-2 mb-1">功能</p>
        <nav className="space-y-0.5">
          {NAV_ITEMS.map(({ href, icon: Icon, label }) => {
            const active = pathname?.startsWith(href);
            return (
              <Link key={href} href={href}
                className={`flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm transition
                  ${active
                    ? "bg-foreground text-background font-medium"
                    : "text-foreground/70 hover:bg-muted/60 hover:text-foreground"}`}>
                <Icon className="w-3.5 h-3.5 shrink-0" />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Divider */}
      <div className="mx-3 my-2 border-t border-border/60" />

      {/* Conversations */}
      <div className="px-4 mb-1.5 flex items-center justify-between">
        <span className="text-[10px] font-semibold text-muted-foreground/50 uppercase tracking-widest">
          对话
        </span>
        <MessagesSquare className="w-3 h-3 text-muted-foreground/30" />
      </div>

      <ul className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5 min-h-0">
        {filtered.length === 0 && search && (
          <li className="px-3 py-4 text-xs text-muted-foreground text-center">无匹配会话</li>
        )}
        {filtered.length === 0 && !search && (
          <li className="px-3 py-6 text-xs text-muted-foreground/50 text-center">
            暂无对话<br />
            <span className="text-[11px]">点击「新建对话」开始</span>
          </li>
        )}
        {filtered.map((c) => {
          const isActive = c.id === activeId;
          return (
            <li key={c.id}
              className={`group flex items-center justify-between px-2.5 py-1.5 rounded-lg
                          text-sm transition cursor-pointer
                          ${isActive ? "bg-muted font-medium" : "hover:bg-muted/50"}`}>
              <Link href={`/c/${c.id}`} className="flex-1 truncate min-w-0 text-[13px]">
                {c.title || "未命名"}
              </Link>
              <button
                className="shrink-0 opacity-0 group-hover:opacity-100 transition-opacity ml-1 p-0.5 rounded"
                onClick={async (e) => {
                  e.preventDefault();
                  await api.deleteConversation(c.id);
                  setConvs((s) => s.filter((x) => x.id !== c.id));
                }}>
                <Trash2 className="w-3 h-3 text-muted-foreground/60 hover:text-red-500 transition-colors" />
              </button>
            </li>
          );
        })}
      </ul>

      {/* Footer */}
      <div className="px-3 pb-3 pt-2 border-t border-border/60">
        <button
          onClick={() => setShowCleanup(true)}
          className="w-full text-[11px] text-muted-foreground/50 hover:text-muted-foreground
                     transition py-1 rounded hover:bg-muted/40 text-center">
          清理空会话
        </button>
      </div>

      {showCleanup && (
        <CleanupDialog onClose={() => setShowCleanup(false)} onPurged={reload} />
      )}
    </aside>
  );
}
