import { create } from "zustand";

export interface ToolCallEntry {
  id: string;
  toolName: string;
  argsPreview: string;
  startedAt: number;
  endedAt?: number;
  status: "running" | "ok" | "error";
  riskLevel?: "low" | "medium" | "high";
  errorMessage?: string;
}

export interface AgentNode {
  id: string;
  name: string;
  taskTitle?: string;
  startedAt: number;
  endedAt?: number;
  status: "running" | "done" | "warning" | "error";
  parentId?: string;
  toolCalls: ToolCallEntry[];
  warnings: string[];
}

interface TimelineState {
  agents: Record<string, AgentNode>;
  rootAgentId: string;
  agentOrder: string[];
  activeStack: string[];                                    // sub-agent stack
  open: boolean;
  ingest: (event: string, data: any) => void;
  clear: () => void;
  toggleOpen: () => void;
  setOpen: (open: boolean) => void;
}

const MAIN_ID = "main";

function now() { return Date.now(); }

function truncate(v: unknown, max = 200): string {
  const s = typeof v === "string" ? v : JSON.stringify(v ?? "");
  return s.length > max ? s.slice(0, max) + "…" : s;
}

export const useTimeline = create<TimelineState>((set, get) => ({
  agents: {},
  rootAgentId: MAIN_ID,
  agentOrder: [],
  activeStack: [MAIN_ID],
  open: false,
  toggleOpen: () => set((s) => ({ open: !s.open })),
  setOpen: (open) => set({ open }),
  clear: () => set({
    agents: {}, agentOrder: [], activeStack: [MAIN_ID],
  }),
  ingest: (event, data) => {
    const state = get();
    const ensureMain = () => {
      if (state.agents[MAIN_ID]) return;
      set((s) => ({
        agents: { ...s.agents, [MAIN_ID]: {
          id: MAIN_ID, name: "main", startedAt: now(),
          status: "running", toolCalls: [], warnings: [],
        }},
        agentOrder: s.agentOrder.includes(MAIN_ID) ? s.agentOrder : [...s.agentOrder, MAIN_ID],
      }));
    };
    const activeId = () => {
      const s = get();
      return s.activeStack[s.activeStack.length - 1] ?? MAIN_ID;
    };
    const patchAgent = (id: string, patch: Partial<AgentNode>) =>
      set((s) => ({
        agents: { ...s.agents, [id]: { ...s.agents[id], ...patch } },
      }));
    const pushTool = (id: string, t: ToolCallEntry) =>
      set((s) => ({
        agents: { ...s.agents, [id]: {
          ...s.agents[id], toolCalls: [...s.agents[id].toolCalls, t],
        }},
      }));
    const patchTool = (agentId: string, callId: string,
                         patch: Partial<ToolCallEntry>) =>
      set((s) => ({
        agents: { ...s.agents, [agentId]: {
          ...s.agents[agentId],
          toolCalls: s.agents[agentId].toolCalls.map((t) =>
            t.id === callId ? { ...t, ...patch } : t),
        }},
      }));

    switch (event) {
      case "sub_agent_start": {
        ensureMain();
        const id: string = data.agent_id;
        const name: string = data.agent_name ?? "sub-agent";
        const parentId = activeId();
        set((s) => ({
          agents: { ...s.agents, [id]: {
            id, name, taskTitle: data.task ?? data.title,
            startedAt: now(), status: "running",
            parentId, toolCalls: [], warnings: [],
          }},
          agentOrder: s.agentOrder.includes(id) ? s.agentOrder : [...s.agentOrder, id],
          activeStack: [...s.activeStack, id],
        }));
        break;
      }
      case "skill_loaded": {
        // 把 skill 子代理也当 sub_agent_start：push 一帧，name="skill:<name>"。
        // run_skill 在 finally 里发对应的 sub_agent_end，已经走上面那个 case。
        ensureMain();
        const id: string = data.agent_id;
        const skillName: string = data.name ?? "skill";
        const parentId = activeId();
        set((s) => ({
          agents: { ...s.agents, [id]: {
            id, name: `skill:${skillName}`,
            taskTitle: data.version ? `v${data.version}` : undefined,
            startedAt: now(), status: "running",
            parentId, toolCalls: [], warnings: [],
          }},
          agentOrder: s.agentOrder.includes(id) ? s.agentOrder : [...s.agentOrder, id],
          activeStack: [...s.activeStack, id],
        }));
        break;
      }
      case "sub_agent_end": {
        const id: string = data.agent_id;
        if (state.agents[id]) {
          patchAgent(id, {
            endedAt: now(),
            status: data.status === "failed" ? "error" : "done",
          });
        }
        set((s) => ({
          activeStack: s.activeStack.filter((x) => x !== id),
        }));
        break;
      }
      case "tool_call_start": {
        ensureMain();
        const aid = activeId();
        pushTool(aid, {
          id: data.call_id, toolName: data.name,
          argsPreview: truncate(data.args), startedAt: now(),
          status: "running",
        });
        break;
      }
      case "tool_call_result": {
        const aid = activeId();
        patchTool(aid, data.call_id, {
          endedAt: now(),
          status: data.ok ? "ok" : "error",
          errorMessage: data.error,
        });
        break;
      }
      case "warning": {
        const aid = activeId();
        const cur = state.agents[aid];
        if (cur) {
          patchAgent(aid, {
            warnings: [...cur.warnings, String(data.message ?? "warning")],
            status: cur.status === "running" ? "warning" : cur.status,
          });
        }
        break;
      }
      case "done": {
        if (state.agents[MAIN_ID]) {
          patchAgent(MAIN_ID, { endedAt: now(), status: "done" });
        }
        break;
      }
      case "error": {
        const aid = activeId();
        if (state.agents[aid]) {
          patchAgent(aid, { endedAt: now(), status: "error" });
        }
        break;
      }
    }
  },
}));
