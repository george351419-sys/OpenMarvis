"use client";
import { Activity, X } from "lucide-react";

import { AgentNode, useTimeline } from "@/lib/stores/timeline";
import { AgentSection } from "./AgentSection";

export function TimelinePanel() {
  const { agents, agentOrder, open, setOpen } = useTimeline();

  if (!open) return null;

  // Render top-level agents (no parent), then nest children inline.
  function renderTree(node: AgentNode, depth: number): JSX.Element {
    const children = agentOrder
      .map((id) => agents[id])
      .filter((a) => a && a.parentId === node.id);
    return (
      <div key={node.id}>
        <AgentSection node={node} depth={depth} />
        {children.map((c) => renderTree(c, depth + 1))}
      </div>
    );
  }

  const roots = agentOrder.map((id) => agents[id]).filter((a) => a && !a.parentId);

  return (
    <aside className="w-[360px] border-l border-border h-screen flex flex-col">
      <div className="px-3 py-2 border-b border-border flex items-center
                        justify-between text-sm">
        <span className="font-medium inline-flex items-center gap-1.5">
          <Activity className="w-4 h-4" /> Timeline
        </span>
        <button onClick={() => setOpen(false)}
                className="p-1 hover:bg-muted/60 rounded" title="收起">
          <X className="w-3 h-3" />
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {roots.length === 0 ? (
          <div className="text-xs text-muted-foreground p-4 text-center">
            尚未开始执行。发送消息后这里会显示工具调用轨迹。
          </div>
        ) : (
          roots.map((r) => renderTree(r, 0))
        )}
      </div>
    </aside>
  );
}

export function TimelineToggle() {
  const { open, toggleOpen } = useTimeline();
  return (
    <button
      type="button"
      onClick={toggleOpen}
      className="p-1.5 rounded hover:bg-muted/60"
      title={open ? "收起 Timeline" : "展开 Timeline"}
    >
      <Activity className="w-4 h-4" />
    </button>
  );
}
