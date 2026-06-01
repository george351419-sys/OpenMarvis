export const SSE_EVENTS = {
  THINKING_DELTA: "thinking_delta",
  CONTENT_DELTA: "content_delta",
  TOOL_CALL_START: "tool_call_start",
  TOOL_CALL_RESULT: "tool_call_result",
  CARD: "card",
  ASK_USER: "ask_user",
  SUB_AGENT_START: "sub_agent_start",
  SUB_AGENT_END: "sub_agent_end",
  WARNING: "warning",
  ERROR: "error",
  DONE: "done",
} as const;

export type SSEEventType = (typeof SSE_EVENTS)[keyof typeof SSE_EVENTS];

export interface ThinkingDeltaPayload { text: string }
export interface ContentDeltaPayload { text: string }
export interface ToolCallStartPayload {
  call_id: string;
  name: string;
  args: Record<string, unknown>;
}
export interface ToolCallResultPayload {
  call_id: string;
  ok: boolean;
  preview?: string;
  error?: string;
}
export interface CardPayload {
  type: string;     // mv-*
  payload: string;  // 卡片 body（markdown 或 JSON 字符串）
}
export interface AskUserPayload {
  title: string;
  display_type: "text" | "image" | "file" | "app";
  form_type: "single_select" | "multi_select" | "confirm";
  options: Array<{ label?: string; description?: string; file_path?: string }>;
}
export interface SubAgentStartPayload { agent_id: string; agent_name: string }
export interface SubAgentEndPayload { agent_id: string; status: "ok" | "failed" }
export interface WarningPayload { message: string }
export interface ErrorPayload { message: string; recoverable: boolean }
export interface DonePayload { final_content?: string }
