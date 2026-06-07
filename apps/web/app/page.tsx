"use client";
import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Upload, X } from "lucide-react";

import { api } from "@/lib/api";
import { ConversationSidebar } from "@/components/ConversationSidebar";
import { HorseLogo } from "@/components/HorseLogo";

// ─── Example prompts ──────────────────────────────────────────────────────────

const TABS = [
  { id: "recommend", label: "推荐" },
  { id: "work",      label: "办公学习" },
  { id: "files",     label: "文件操作" },
  { id: "search",    label: "网络搜索" },
  { id: "schedule",  label: "定时任务" },
];

const PROMPTS: Record<string, { emoji: string; title: string; text: string }[]> = {
  recommend: [
    { emoji: "📁", title: "整理下载文件夹",   text: "帮我把 ~/Downloads 文件夹里的文件按类型整理好，图片、文档、压缩包分开放" },
    { emoji: "📊", title: "白皮书秒变 PPT",   text: "帮我做一个关于「大模型技术趋势」的 PPT，5 页，图文并茂" },
    { emoji: "🔍", title: "深度调研报告",     text: "帮我调研 2025 年 AI 编程工具市场格局，输出一份结构化报告" },
    { emoji: "⏰", title: "每日提醒助手",     text: "帮我设置每天早上 9 点的晨会提醒，和每天下午 6 点的下班备份提醒" },
    { emoji: "📄", title: "搜索合同文件",     text: "帮我在 ~/Documents 里找最近三个月的合同 PDF 文件" },
    { emoji: "✍️", title: "写产品介绍文档",   text: "帮我写一份 OpenMarvis AI 助手的产品介绍，保存为 Word 格式" },
  ],
  work: [
    { emoji: "📝", title: "生成会议纪要",     text: "帮我把这段内容整理成一份正式的会议纪要文档" },
    { emoji: "📊", title: "Excel 数据分析",   text: "帮我分析桌面上的 Excel 文件，生成数据摘要" },
    { emoji: "✉️", title: "写商务邮件",       text: "帮我写一封关于项目进度汇报的专业商务邮件" },
    { emoji: "📋", title: "制作简历模板",     text: "帮我创建一个现代风格的简历 Word 文档模板" },
    { emoji: "🗂️", title: "整理文档目录",    text: "帮我把 ~/Documents 里的文件按项目名称分类整理" },
    { emoji: "📈", title: "季度汇报 PPT",     text: "帮我做一份季度工作汇报 PPT，10 页，包含数据图表" },
  ],
  files: [
    { emoji: "🔍", title: "查找桌面 PDF",     text: "帮我找一下桌面上所有的 PDF 文件" },
    { emoji: "🗂️", title: "整理下载文件夹",  text: "帮我整理 ~/Downloads，按图片/文档/视频自动分类" },
    { emoji: "📦", title: "截图批量重命名",   text: "帮我把桌面上所有截图按「Screenshot_日期」格式批量重命名" },
    { emoji: "🖼️", title: "搜索风景照片",    text: "帮我在图库里找有没有风景照片" },
    { emoji: "🗑️", title: "清理重复文件",    text: "帮我找出 ~/Downloads 里的重复文件并列出清单" },
    { emoji: "📤", title: "AirDrop 发送文件", text: "帮我把桌面上最新的文件通过 AirDrop 发给我的 iPhone" },
  ],
  search: [
    { emoji: "🌤", title: "今日天气查询",     text: "今天上海天气怎么样，要出门需要带伞吗" },
    { emoji: "🤖", title: "AI 模型横向对比",  text: "帮我对比 Claude 4 和 GPT-4o 的主要优缺点，整理成表格" },
    { emoji: "📰", title: "科技行业简报",     text: "帮我整理今天最重要的 AI 行业新闻，写成简报" },
    { emoji: "🔗", title: "读取指定网页",     text: "帮我读取 https://github.com/trending 并总结热门项目" },
    { emoji: "📚", title: "学术调研 RAG",     text: "帮我调研最新的 RAG 检索增强技术进展，输出综述" },
    { emoji: "💹", title: "大模型创业分析",   text: "帮我分析主流大模型创业公司的商业模式差异" },
  ],
  schedule: [
    { emoji: "⏰", title: "每日晨会提醒",     text: "帮我设置每天早上 9 点的晨会提醒" },
    { emoji: "💧", title: "每两小时喝水",     text: "帮我设置每隔 2 小时的喝水提醒" },
    { emoji: "📅", title: "明天交周报",       text: "明天下午 3 点提醒我交周报" },
    { emoji: "🔄", title: "每周工作总结",     text: "每周一上午 10 点提醒我整理上周工作总结" },
    { emoji: "💾", title: "每日备份提醒",     text: "每天下午 6 点提醒我备份重要文件" },
    { emoji: "📊", title: "每周五工作简报",   text: "每周五下午 5 点帮我自动生成本周工作简报" },
  ],
};

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function HomePage() {
  const router    = useRouter();
  const [input, setInput]     = useState("");
  const [tab, setTab]         = useState("recommend");
  const [sending, setSending] = useState(false);
  const [error, setError]     = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [pendingFiles, setPendingFiles] = useState<File[]>([]);

  async function start(text: string) {
    if (!text.trim() && pendingFiles.length === 0) return;
    if (sending) return;
    setSending(true);
    setError(null);
    try {
      const conv = await api.createConversation("");
      if (pendingFiles.length > 0) {
        const paths: string[] = [];
        for (const f of pendingFiles) {
          const out = await api.upload(conv.id, f);
          paths.push(...out.map((x) => x.saved_path));
        }
        sessionStorage.setItem(`chat_prefill_files_${conv.id}`, JSON.stringify(paths));
      }
      if (text.trim()) sessionStorage.setItem(`chat_prefill_${conv.id}`, text.trim());
      window.location.href = `/c/${conv.id}`;
    } catch (e: any) {
      setError("无法连接后端，请确认服务已启动");
      setSending(false);
    }
  }

  function addFiles(files: FileList | null) {
    if (!files) return;
    setPendingFiles((s) => [...s, ...Array.from(files)]);
    if (fileInputRef.current) fileInputRef.current.value = "";
  }

  const prompts = PROMPTS[tab] ?? PROMPTS.recommend;

  return (
    <div className="flex h-screen overflow-hidden">
      <ConversationSidebar />

      <main className="flex-1 min-w-0 overflow-y-auto">
        <div className="min-h-full flex flex-col items-center px-6 pt-[9vh] pb-16">

          {/* Avatar + tagline */}
          <div className="flex flex-col items-center gap-3 mb-8">
            <HorseLogo size={80} className="shadow-xl rounded-[22px]" />
            <div className="text-center">
              <h1 className="text-[26px] font-bold tracking-tight leading-none">OpenMarvis</h1>
              <p className="text-sm text-muted-foreground mt-2">马维斯 为你 24 小时随时在线</p>
            </div>
          </div>

          {/* Input */}
          <div className="w-full max-w-[680px] mb-8">
            {pendingFiles.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mb-2 px-1">
                {pendingFiles.map((f, i) => (
                  <span key={i}
                    className="inline-flex items-center gap-1 text-xs bg-muted border border-border
                               rounded-lg px-2 py-1 text-muted-foreground">
                    {f.name}
                    <button onClick={() => setPendingFiles((s) => s.filter((_, j) => j !== i))}
                            className="hover:text-foreground cursor-pointer">
                      <X className="w-3 h-3" />
                    </button>
                  </span>
                ))}
              </div>
            )}
            <div className="relative rounded-2xl border border-border bg-background shadow-sm
                            focus-within:ring-2 focus-within:ring-ring/40 transition-shadow">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); start(input); }
                }}
                placeholder="请输入任务，交给我来帮你完成"
                rows={4}
                disabled={sending}
                className="w-full resize-none rounded-2xl px-5 pt-4 pb-14 text-sm bg-transparent
                           focus:outline-none placeholder:text-muted-foreground/40 disabled:opacity-50"
              />
              <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-4 pb-3">
                {/* Left: file upload */}
                <label className="inline-flex items-center gap-1.5 cursor-pointer text-xs
                                  text-muted-foreground hover:text-foreground transition
                                  px-2 py-1 rounded-lg hover:bg-muted/50">
                  <Upload className="w-3.5 h-3.5" />
                  选择文件
                  <input ref={fileInputRef} type="file" multiple className="hidden"
                         onChange={(e) => addFiles(e.target.files)} />
                </label>
                {/* Right: send button */}
                <button
                  onClick={() => start(input)}
                  disabled={(!input.trim() && pendingFiles.length === 0) || sending}
                  className="w-9 h-9 rounded-full bg-foreground text-background flex items-center
                             justify-center disabled:opacity-25 transition hover:opacity-80 active:scale-95"
                >
                  {sending ? (
                    <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="3"
                              strokeDasharray="40" strokeDashoffset="15" />
                    </svg>
                  ) : (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none">
                      <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" strokeWidth="2.5"
                            strokeLinecap="round" strokeLinejoin="round"/>
                    </svg>
                  )}
                </button>
              </div>
            </div>
          </div>

          {/* Error banner */}
          {error && (
            <div className="w-full max-w-[680px] mb-4 px-4 py-2.5 rounded-xl bg-red-50 border border-red-200
                            text-sm text-red-600 flex items-center justify-between">
              {error}
              <button onClick={() => setError(null)} className="text-red-400 hover:text-red-600 cursor-pointer ml-3">✕</button>
            </div>
          )}

          {/* Tabs */}
          <div className="w-full max-w-[680px] mb-5">
            <div className="flex border-b border-border">
              {TABS.map((t) => (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={`cursor-pointer px-4 py-2.5 text-sm font-medium transition border-b-2 -mb-px ${
                    tab === t.id
                      ? "border-foreground text-foreground"
                      : "border-transparent text-muted-foreground hover:text-foreground"
                  }`}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>

          {/* Prompt cards */}
          <div className="w-full max-w-[680px] grid grid-cols-3 gap-3">
            {prompts.map((p) => (
              <button key={p.title} onClick={() => { setInput(p.text); textareaRef.current?.focus(); }} disabled={sending}
                className="cursor-pointer group text-left p-4 rounded-xl border border-border bg-background
                           hover:border-foreground/30 hover:shadow-md hover:-translate-y-0.5
                           active:scale-[.98] transition-all disabled:opacity-40 disabled:cursor-not-allowed">
                <div className="text-xl mb-2.5 leading-none">{p.emoji}</div>
                <p className="text-sm font-semibold leading-snug mb-1.5">{p.title}</p>
                <p className="text-xs text-muted-foreground line-clamp-2 leading-relaxed">{p.text}</p>
                <div className="mt-3 flex items-center gap-1 opacity-0 group-hover:opacity-60 transition-opacity text-muted-foreground">
                  <span className="text-[10px]">发送</span>
                  <svg width="10" height="10" viewBox="0 0 24 24" fill="none">
                    <path d="M12 19V5M5 12l7-7 7 7" stroke="currentColor" strokeWidth="2.5"
                          strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </button>
            ))}
          </div>

        </div>
      </main>
    </div>
  );
}
