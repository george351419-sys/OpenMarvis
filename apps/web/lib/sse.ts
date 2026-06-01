export interface SSEHandler {
  onEvent: (event: string, data: unknown) => void;
  onError?: (err: Error) => void;
  onClose?: () => void;
}

export function openSSE(path: string, handler: SSEHandler): () => void {
  const url = path.startsWith("/api/proxy") ? path : `/api/proxy${path}`;
  const es = new EventSource(url);
  es.onmessage = (ev) => {
    try { handler.onEvent("message", JSON.parse(ev.data)); }
    catch { handler.onEvent("message", ev.data); }
  };
  // Named events
  ["thinking_delta", "content_delta", "tool_call_start", "tool_call_result",
   "card", "ask_user", "sub_agent_start", "sub_agent_end",
   "warning", "error", "done"].forEach((name) => {
    es.addEventListener(name, (ev: MessageEvent) => {
      try { handler.onEvent(name, JSON.parse(ev.data)); }
      catch { handler.onEvent(name, ev.data); }
    });
  });
  es.onerror = (e) => {
    handler.onError?.(new Error("SSE error"));
    es.close();
    handler.onClose?.();
  };
  return () => es.close();
}
