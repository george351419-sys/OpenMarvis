"use client";

import { useEffect, useRef, useState } from "react";

import { FilePreviewPanel } from "./FilePreviewPanel";
import { FileUploader } from "./FileUploader";
import { MessageBubble } from "./MessageBubble";
import { TimelineToggle } from "./timeline/TimelinePanel";
import { api } from "@/lib/api";
import { streamChat } from "@/lib/streamChat";
import { useChat } from "@/lib/store";
import { useFilePreview } from "@/lib/stores/filePreview";
import { useTimeline } from "@/lib/stores/timeline";

export function ChatStream({ convId }: { convId: string }) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const store = useChat();
  const timeline = useTimeline();
  const previewPath = useFilePreview((s) => s.path);
  const autoSentRef = useRef(false);
  const hasNamedRef = useRef(false);

  const stop = () => {
    abortRef.current?.abort();
    abortRef.current = null;
    setBusy(false);
    store.finishTurn();
  };

  const send = async () => {
    if (!input.trim() && attachments.length === 0) return;
    const text = input.trim();
    const isFirst = store.userMessages.length === 0 && !hasNamedRef.current;
    atBottomRef.current = true;
    store.recordUser(text);
    store.beginAssistantTurn();
    if (isFirst) {
      hasNamedRef.current = true;
      const title = text.slice(0, 25) + (text.length > 25 ? "…" : "");
      api.renameConversation(convId, title).catch(() => {});
    }
    setInput("");
    setBusy(true);
    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await streamChat({ conv_id: convId, message: text, attachments }, {
        onEvent: (ev, data) => {
          timeline.ingest(ev, data);
          switch (ev) {
            case "thinking_delta": store.appendThinking(data.text); break;
            case "content_delta": store.appendContent(data.text); break;
            case "tool_call_start":
              store.toolStart({ call_id: data.call_id, name: data.name, args: data.args }); break;
            case "tool_call_result":
              store.toolResult(data.call_id, data.ok, data.preview, data.error); break;
            case "card": store.pushCard({ type: data.type, payload: data.payload }); break;
            case "ask_user":
              store.setAsk({ ask_id: data.ask_id, title: data.title,
                              form_type: data.form_type, display_type: data.display_type,
                              options: data.options });
              store.pushCard({ type: "mv-ask-user", payload: JSON.stringify(data) });
              break;
            case "sub_agent_start": store.subAgentStart(data.agent_id, data.agent_name); break;
            case "sub_agent_end": store.subAgentEnd(data.agent_id, data.status); break;
            case "done": store.finishTurn(); break;
            case "error":
              store.setError(data.message || "未知错误");
              store.finishTurn();
              break;
          }
        },
        onClose: () => { setBusy(false); abortRef.current = null; },
      }, ctrl.signal);
      setAttachments([]);
    } finally { setBusy(false); abortRef.current = null; }
  };

  const scrollRef = useRef<HTMLDivElement>(null);
  const atBottomRef = useRef(true);

  // 检测用户是否手动上滑
  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    atBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  };

  // 仅当用户在底部时才自动滚动
  useEffect(() => {
    if (atBottomRef.current) {
      scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
    }
  });

  // Auto-send prefilled message from sessionStorage (set by schedules/docs pages)
  useEffect(() => {
    if (autoSentRef.current) return;
    const key = `chat_prefill_${convId}`;
    const msg = sessionStorage.getItem(key);
    if (msg) {
      sessionStorage.removeItem(key);
      const filesKey = `chat_prefill_files_${convId}`;
      let preFiles: string[] = [];
      try { preFiles = JSON.parse(sessionStorage.getItem(filesKey) ?? "[]"); } catch {}
      sessionStorage.removeItem(filesKey);
      autoSentRef.current = true;
      setInput(msg);
      // Defer one tick so input state propagates before send
      setTimeout(() => {
        setInput("");
        atBottomRef.current = true;
        store.recordUser(msg);
        store.beginAssistantTurn();
        if (!hasNamedRef.current) {
          hasNamedRef.current = true;
          const title = msg.slice(0, 25) + (msg.length > 25 ? "…" : "");
          api.renameConversation(convId, title).catch(() => {});
        }
        setBusy(true);
        const ctrl = new AbortController();
        abortRef.current = ctrl;
        streamChat({ conv_id: convId, message: msg, attachments: preFiles }, {
          onEvent: (ev, data) => {
            timeline.ingest(ev, data);
            switch (ev) {
              case "thinking_delta": store.appendThinking(data.text); break;
              case "content_delta": store.appendContent(data.text); break;
              case "tool_call_start":
                store.toolStart({ call_id: data.call_id, name: data.name, args: data.args }); break;
              case "tool_call_result":
                store.toolResult(data.call_id, data.ok, data.preview, data.error); break;
              case "card": store.pushCard({ type: data.type, payload: data.payload }); break;
              case "done": store.finishTurn(); break;
              case "error": store.setError(data.message || "未知错误"); store.finishTurn(); break;
            }
          },
          onClose: () => { setBusy(false); abortRef.current = null; },
        }, ctrl.signal).finally(() => { setBusy(false); abortRef.current = null; });
      }, 50);
    }
  }, [convId]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="flex h-screen overflow-hidden">
      <div className="flex flex-col flex-1 min-w-0">
      <div className="px-3 py-2 border-b border-border flex items-center
                        justify-end gap-1">
        <TimelineToggle />
      </div>
      <div ref={scrollRef} onScroll={onScroll} className="flex-1 overflow-y-auto p-6">
        {store.userMessages.map((m, i) => (
          <div key={m.id}>
            <MessageBubble role="user" text={m.text} />
            {store.assistant[i] && (
              <MessageBubble role="assistant" turn={store.assistant[i]} convId={convId} />
            )}
          </div>
        ))}
      </div>
      {/* Input area — Marvis style */}
      <div className="border-t border-border px-4 pt-3 pb-4 bg-background">
        {attachments.length > 0 && (
          <div className="text-xs text-muted-foreground mb-2 px-1">
            附件：{attachments.length} 个
          </div>
        )}
        <div className="relative rounded-2xl border border-border bg-background
                        focus-within:ring-2 focus-within:ring-ring/40 transition-shadow">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
            }}
            disabled={busy}
            placeholder="请输入任务，交给我来帮你完成"
            className="w-full resize-none rounded-2xl px-4 pt-3 pb-12 text-sm bg-transparent
                       focus:outline-none placeholder:text-muted-foreground/40 disabled:opacity-50"
            rows={3}
          />
          {/* Bottom bar */}
          <div className="absolute bottom-0 left-0 right-0 flex items-center justify-between px-3 pb-2.5">
            {/* Left: file uploader */}
            <FileUploader
              convId={convId}
              onUploaded={(paths) => setAttachments((s) => [...s, ...paths])}
              label="+ 选择文件"
              className="inline-flex items-center gap-1 text-xs text-muted-foreground
                         hover:text-foreground cursor-pointer transition px-2 py-1 rounded-lg
                         border border-transparent hover:border-border hover:bg-muted/50"
            />
            {/* Right: stop / send */}
            {busy ? (
              <button onClick={stop}
                className="w-8 h-8 flex items-center justify-center rounded-full
                           bg-red-500 hover:bg-red-600 cursor-pointer transition">
                <span className="w-3 h-3 rounded-sm bg-white inline-block" />
              </button>
            ) : (
              <button onClick={send}
                disabled={!input.trim() && attachments.length === 0}
                className="w-8 h-8 flex items-center justify-center rounded-full cursor-pointer
                           transition disabled:opacity-30 hover:opacity-80 active:scale-95"
                style={{
                  background: (input.trim() || attachments.length > 0) ? "#111" : "#e5e7eb",
                }}>
                <svg width="13" height="13" viewBox="0 0 24 24" fill="none">
                  <path d="M12 19V5M5 12l7-7 7 7" stroke="white" strokeWidth="2.5"
                        strokeLinecap="round" strokeLinejoin="round"/>
                </svg>
              </button>
            )}
          </div>
        </div>
        <p className="text-[10px] text-muted-foreground/40 text-center mt-2 select-none">
          Enter 发送 · Shift+Enter 换行
        </p>
      </div>
      </div>
      {previewPath && <FilePreviewPanel />}
    </div>
  );
}
