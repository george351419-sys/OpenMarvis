import { create } from "zustand";

export interface ToolTrace {
  call_id: string;
  name: string;
  args: Record<string, unknown>;
  ok?: boolean;
  preview?: string;
  error?: string;
}

export interface CardItem { type: string; payload: string }

export interface AssistantTurn {
  id: string;
  content: string;
  thinking: string;
  tools: ToolTrace[];
  cards: CardItem[];
  subAgents: Array<{ agent_id: string; agent_name: string; status?: string }>;
  done: boolean;
  error?: string;
}

interface AskUserState {
  ask_id: string;
  title: string;
  form_type: "single_select" | "multi_select" | "confirm";
  display_type: "text" | "image" | "file" | "app";
  options: Array<{ label?: string; description?: string; file_path?: string }>;
}

interface ChatState {
  userMessages: Array<{ id: string; text: string }>;
  assistant: AssistantTurn[];
  currentAsk: AskUserState | null;
  beginAssistantTurn: () => void;
  appendContent: (text: string) => void;
  appendThinking: (text: string) => void;
  toolStart: (t: ToolTrace) => void;
  toolResult: (call_id: string, ok: boolean, preview?: string, error?: string) => void;
  pushCard: (card: CardItem) => void;
  subAgentStart: (id: string, name: string) => void;
  subAgentEnd: (id: string, status: string) => void;
  setAsk: (a: AskUserState | null) => void;
  finishTurn: () => void;
  recordUser: (text: string) => void;
  reset: () => void;
}

function genId(): string {
  return Math.random().toString(36).slice(2, 12);
}

export const useChat = create<ChatState>((set) => ({
  userMessages: [],
  assistant: [],
  currentAsk: null,
  beginAssistantTurn: () =>
    set((s) => ({
      assistant: [...s.assistant,
        { id: genId(), content: "", thinking: "", tools: [], cards: [],
          subAgents: [], done: false }],
    })),
  appendContent: (text) =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      list[list.length - 1] = { ...cur, content: cur.content + text };
      return { assistant: list };
    }),
  appendThinking: (text) =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      list[list.length - 1] = { ...cur, thinking: cur.thinking + text };
      return { assistant: list };
    }),
  toolStart: (t) =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      list[list.length - 1] = { ...cur, tools: [...cur.tools, t] };
      return { assistant: list };
    }),
  toolResult: (call_id, ok, preview, error) =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      const tools = cur.tools.map((t) =>
        t.call_id === call_id ? { ...t, ok, preview, error } : t);
      list[list.length - 1] = { ...cur, tools };
      return { assistant: list };
    }),
  pushCard: (card) =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      list[list.length - 1] = { ...cur, cards: [...cur.cards, card] };
      return { assistant: list };
    }),
  subAgentStart: (agent_id, agent_name) =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      list[list.length - 1] = {
        ...cur, subAgents: [...cur.subAgents, { agent_id, agent_name }],
      };
      return { assistant: list };
    }),
  subAgentEnd: (agent_id, status) =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      const subs = cur.subAgents.map((sa) =>
        sa.agent_id === agent_id ? { ...sa, status } : sa);
      list[list.length - 1] = { ...cur, subAgents: subs };
      return { assistant: list };
    }),
  setAsk: (a) => set({ currentAsk: a }),
  finishTurn: () =>
    set((s) => {
      const list = [...s.assistant];
      const cur = list[list.length - 1]; if (!cur) return {} as any;
      list[list.length - 1] = { ...cur, done: true };
      return { assistant: list };
    }),
  recordUser: (text) =>
    set((s) => ({ userMessages: [...s.userMessages, { id: genId(), text }] })),
  reset: () => set({ userMessages: [], assistant: [], currentAsk: null }),
}));
