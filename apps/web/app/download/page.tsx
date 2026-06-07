"use client";
import { useState } from "react";
import Link from "next/link";
import { CheckCircle2, ChevronRight, Download, Monitor, Terminal } from "lucide-react";

import { ConversationSidebar } from "@/components/ConversationSidebar";
import { HorseLogo } from "@/components/HorseLogo";

const STEPS = [
  {
    step: 1,
    title: "安装依赖",
    cmd: "cd apps/desktop && npm install",
    desc: "安装 Electron 和打包工具",
  },
  {
    step: 2,
    title: "生成安装包",
    cmd: "npm run build:dmg",
    desc: "构建 macOS DMG 安装文件（约 1-2 分钟）",
  },
  {
    step: 3,
    title: "安装应用",
    desc: "打开 apps/desktop/dist/ 目录，双击 OpenMarvis.dmg，拖到应用程序文件夹",
  },
];

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
      className="shrink-0 text-[10px] px-2 py-0.5 rounded border border-border hover:bg-muted transition text-muted-foreground"
    >
      {copied ? "已复制" : "复制"}
    </button>
  );
}

export default function DownloadPage() {
  return (
    <div className="flex h-screen overflow-hidden">
      <ConversationSidebar />
      <main className="flex-1 min-w-0 overflow-y-auto bg-muted/20">
        <div className="max-w-2xl mx-auto px-6 py-10">

          {/* Header */}
          <div className="flex items-center gap-4 mb-8">
            <HorseLogo size={56} />
            <div>
              <h1 className="text-xl font-bold">OpenMarvis 桌面版</h1>
              <p className="text-sm text-muted-foreground mt-0.5">
                安装后无需浏览器，直接在桌面使用 AI 助手
              </p>
            </div>
          </div>

          {/* Feature cards */}
          <div className="grid grid-cols-3 gap-3 mb-8">
            {[
              { icon: Monitor, title: "原生窗口体验", desc: "macOS 原生标题栏和操作方式" },
              { icon: Download, title: "系统托盘常驻", desc: "后台运行，随时唤出对话框" },
              { icon: CheckCircle2, title: "与 Web 版同步", desc: "共用同一后端，数据完全一致" },
            ].map(({ icon: Icon, title, desc }) => (
              <div key={title} className="p-4 rounded-xl border border-border bg-background">
                <Icon className="w-5 h-5 text-muted-foreground mb-2" />
                <p className="text-sm font-semibold mb-1">{title}</p>
                <p className="text-xs text-muted-foreground leading-relaxed">{desc}</p>
              </div>
            ))}
          </div>

          {/* Quick start — dev mode */}
          <div className="mb-6 p-5 rounded-xl border border-border bg-background">
            <div className="flex items-center gap-2 mb-3">
              <Terminal className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-semibold">开发模式（无需打包）</span>
              <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-50 text-emerald-600 border border-emerald-200">推荐</span>
            </div>
            <p className="text-xs text-muted-foreground mb-3 leading-relaxed">
              确保后端和 Web 服务已启动，然后运行以下命令立即打开桌面窗口：
            </p>
            <div className="space-y-2">
              {[
                "cd apps/desktop",
                "npm install",
                "npm start",
              ].map((cmd) => (
                <div key={cmd} className="flex items-center gap-2 bg-muted/50 rounded-lg px-3 py-2">
                  <code className="text-xs font-mono flex-1 text-foreground">{cmd}</code>
                  <CopyButton text={cmd} />
                </div>
              ))}
            </div>
          </div>

          {/* Build DMG */}
          <div className="mb-6 p-5 rounded-xl border border-border bg-background">
            <div className="flex items-center gap-2 mb-3">
              <Download className="w-4 h-4 text-muted-foreground" />
              <span className="text-sm font-semibold">打包安装包（生成 .dmg）</span>
            </div>
            <div className="space-y-4">
              {STEPS.map(({ step, title, cmd, desc }) => (
                <div key={step} className="flex gap-4">
                  <div className="w-6 h-6 rounded-full bg-foreground text-background flex items-center justify-center text-xs font-bold shrink-0 mt-0.5">
                    {step}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm font-semibold mb-0.5">{title}</p>
                    <p className="text-xs text-muted-foreground mb-1.5 leading-relaxed">{desc}</p>
                    {cmd && (
                      <div className="flex items-center gap-2 bg-muted/50 rounded-lg px-3 py-2">
                        <code className="text-xs font-mono flex-1 text-foreground">{cmd}</code>
                        <CopyButton text={cmd} />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Tip */}
          <div className="p-4 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-800 leading-relaxed">
            <strong>注意：</strong>桌面版需要后端服务（端口 8000）和 Web 服务（端口 3000）在本地运行。
            打开桌面客户端前，请确认两个服务均已启动。
          </div>

          <div className="mt-6 text-center">
            <Link href="/" className="text-xs text-muted-foreground hover:text-foreground transition inline-flex items-center gap-1">
              返回主页 <ChevronRight className="w-3 h-3" />
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
