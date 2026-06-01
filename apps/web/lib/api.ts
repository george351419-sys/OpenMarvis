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

export const api = {
  listConversations: () => fetchJson<ConversationDTO[]>("/conversations"),
  createConversation: (title: string) =>
    fetchJson<ConversationDTO>("/conversations", { method: "POST", body: JSON.stringify({ title }) }),
  deleteConversation: (id: string) =>
    fetchJson<{ ok: boolean }>(`/conversations/${id}`, { method: "DELETE" }),
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
  putSettings: (patch: any) =>
    fetchJson<any>("/settings", { method: "PUT", body: JSON.stringify(patch) }),
};
