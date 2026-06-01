export interface ChatStreamHandler {
  onEvent: (event: string, data: any) => void;
  onClose?: () => void;
}

export async function streamChat(payload: { conv_id: string; message: string;
                                              attachments: string[] },
                                  handler: ChatStreamHandler): Promise<void> {
  const res = await fetch("/api/proxy/chat", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok || !res.body) {
    handler.onEvent("error", { message: `HTTP ${res.status}`, recoverable: false });
    handler.onClose?.();
    return;
  }
  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let currentEvent: string | null = null;
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const lines = buf.split("\n");
    buf = lines.pop() ?? "";
    for (const raw of lines) {
      const line = raw.trim();
      if (!line) { currentEvent = null; continue; }
      if (line.startsWith("event:")) {
        currentEvent = line.slice(6).trim();
      } else if (line.startsWith("data:") && currentEvent) {
        const data = line.slice(5).trim();
        try { handler.onEvent(currentEvent, JSON.parse(data)); }
        catch { handler.onEvent(currentEvent, data); }
      }
    }
  }
  handler.onClose?.();
}
