"use client";

import { useState } from "react";

import { FileUploader } from "./FileUploader";
import { MessageBubble } from "./MessageBubble";
import { TimelineToggle } from "./timeline/TimelinePanel";
import { streamChat } from "@/lib/streamChat";
import { useChat } from "@/lib/store";
import { useTimeline } from "@/lib/stores/timeline";

export function ChatStream({ convId }: { convId: string }) {
  const [input, setInput] = useState("");
  const [attachments, setAttachments] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const store = useChat();
  const timeline = useTimeline();

  const send = async () => {
    if (!input.trim() && attachments.length === 0) return;
    const text = input.trim();
    store.recordUser(text);
    store.beginAssistantTurn();
    setInput("");
    setBusy(true);
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
        onClose: () => setBusy(false),
      });
      setAttachments([]);
    } finally { setBusy(false); }
  };

  return (
    <div className="flex flex-col h-screen">
      <div className="px-3 py-2 border-b border-border flex items-center
                        justify-end gap-1">
        <TimelineToggle />
      </div>
      <div className="flex-1 overflow-y-auto p-6">
        {store.userMessages.map((m, i) => (
          <div key={m.id}>
            <MessageBubble role="user" text={m.text} />
            {store.assistant[i] && (
              <MessageBubble role="assistant" turn={store.assistant[i]} convId={convId} />
            )}
          </div>
        ))}
      </div>
      <div className="border-t border-border p-3 space-y-2">
        {attachments.length > 0 && (
          <div className="text-xs text-muted-foreground">
            附件: {attachments.length} 个
          </div>
        )}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) { e.preventDefault(); send(); }
            }}
            disabled={busy}
            placeholder="说点什么…（⌘/Ctrl + Enter 发送）"
            className="flex-1 resize-none rounded border border-border p-2 text-sm bg-background"
            rows={3}
          />
          <div className="flex flex-col gap-1">
            <FileUploader convId={convId}
                          onUploaded={(paths) => setAttachments((s) => [...s, ...paths])} />
            <button onClick={send} disabled={busy}
                    className="px-3 py-1 text-sm rounded bg-foreground text-background hover:opacity-90 disabled:opacity-40">
              {busy ? "..." : "发送"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
