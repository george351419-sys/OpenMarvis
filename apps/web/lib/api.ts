const BASE = "/api/proxy";

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
  return res.json();
}

export interface ConversationDTO {
  id: string; title: string; created_at: number; updated_at: number;
}
export interface MessageDTO {
  id: number; role: string; content: string; thinking: string; created_at: number;
}
export interface NotificationDTO {
  id: number;
  origin_conv_id: string;
  schedule_id: string;
  virtual_conv_id: string;
  summary: string;
  status: "success" | "failed";
  created_at: number;
}
export interface ScheduleDTO {
  id: string;
  origin_conv_id: string;
  trigger_type: "once" | "interval" | "cron";
  trigger_spec: string;
  instruction: string;
  description: string;
  next_run_at: string | null;
}
export interface SkillParamDTO {
  type: string;
  description: string;
  required: boolean;
  enum: string[] | null;
  default: unknown;
}
export interface SkillDTO {
  name: string;
  version: string;
  description: string;
  author: string;
  license: string;
  risk: "low" | "medium" | "high";
  params: Record<string, SkillParamDTO>;
  allowed_tools: string[];
}

export const api = {
  listConversations: () => fetchJson<ConversationDTO[]>("/conversations"),
  createConversation: (title: string) =>
    fetchJson<ConversationDTO>("/conversations", { method: "POST", body: JSON.stringify({ title }) }),
  renameConversation: (id: string, title: string) =>
    fetchJson<ConversationDTO>(`/conversations/${id}`, {
      method: "PATCH", body: JSON.stringify({ title }),
    }),
  deleteConversation: (id: string) =>
    fetchJson<{ ok: boolean }>(`/conversations/${id}`, { method: "DELETE" }),
  purgeConversation: (id: string) =>
    fetchJson<{ ok: boolean; purged: Record<string, number> }>(
      `/conversations/${id}/purge`, { method: "POST" },
    ),
  cleanupConversations: (filter: {
    empty_title?: boolean;
    min_age_days?: number;
    max_messages?: number;
    include_archived?: boolean;
    dry_run?: boolean;
  }) =>
    fetchJson<
      { dry_run: true; would_purge: number; sample_ids: string[] }
      | { dry_run: false; purged: number; by_table: Record<string, number> }
    >("/conversations/cleanup", {
      method: "POST", body: JSON.stringify(filter),
    }),
  listMessages: (id: string) => fetchJson<MessageDTO[]>(`/conversations/${id}/messages`),
  upload: async (convId: string, file: File) => {
    const fd = new FormData(); fd.append("file", file);
    const res = await fetch(`${BASE}/files/upload?conv_id=${convId}`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(`upload failed: ${res.status}`);
    return res.json() as Promise<Array<{ original_name: string; saved_path: string }>>;
  },
  answerAsk: (conv_id: string, ask_id: string, choices: string[]) =>
    fetchJson<{ ok: boolean }>("/asks/answer", {
      method: "POST", body: JSON.stringify({ conv_id, ask_id, choices }),
    }),
  getSettings: () => fetchJson<any>("/settings"),
  getSettingsInfo: () => fetchJson<any>("/settings/info"),
  getSettingsHealth: () => fetchJson<any>("/settings/health"),
  getConfigPath: () => fetchJson<any>("/settings/config-path"),
  reloadConfig: () => fetchJson<any>("/settings/reload", { method: "POST" }),
  testApiConnection: () => fetchJson<any>("/settings/test-connection", { method: "POST" }),
  putSettings: (patch: any) =>
    fetchJson<any>("/settings", { method: "PUT", body: JSON.stringify(patch) }),
  listUnreadNotifications: (originConvId?: string) => {
    const qs = originConvId ? `?origin_conv_id=${encodeURIComponent(originConvId)}` : "";
    return fetchJson<NotificationDTO[]>(`/notifications/unread${qs}`);
  },
  markNotificationRead: (id: number) =>
    fetchJson<{ ok: boolean }>(`/notifications/${id}/read`, { method: "POST" }),
  listSchedules: () => fetchJson<ScheduleDTO[]>("/schedules"),
  cancelSchedule: (id: string) =>
    fetchJson<{ ok: boolean }>(`/schedules/${id}`, { method: "DELETE" }),
  listSkills: () => fetchJson<SkillDTO[]>("/skills"),
};
