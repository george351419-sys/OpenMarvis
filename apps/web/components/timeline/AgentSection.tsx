import { useState } from "react";
import { ChevronDown, ChevronRight, TriangleAlert } from "lucide-react";

import { AgentNode } from "@/lib/stores/timeline";
import { DurationLabel } from "./DurationLabel";
import { ToolCallRow } from "./ToolCallRow";

export function AgentSection({ node, depth = 0 }:
    { node: AgentNode; depth?: number }) {
  const [open, setOpen] = useState(true);
  const statusDot =
    node.status === "running" ? "bg-blue-500 animate-pulse" :
    node.status === "error"   ? "bg-red-500" :
    node.status === "warning" ? "bg-amber-500" :
                                   "bg-emerald-500";
  return (
    <div className="border-l border-border" style={{ marginLeft: depth * 12 }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-2 py-1 hover:bg-muted/50 rounded"
      >
        {open ? <ChevronDown className="w-3 h-3" /> : <ChevronRight className="w-3 h-3" />}
        <span className={`inline-block w-2 h-2 rounded-full ${statusDot}`} />
        <span className="text-xs font-medium flex-1 text-left truncate">
          {node.name}
          {node.taskTitle && (
            <span className="text-muted-foreground"> · {node.taskTitle}</span>
          )}
        </span>
        {node.warnings.length > 0 && (
          <TriangleAlert className="w-3 h-3 text-amber-500" />
        )}
        <span className="text-[10px] text-muted-foreground">
          {node.toolCalls.length} 工具
        </span>
        <DurationLabel startedAt={node.startedAt} endedAt={node.endedAt} />
      </button>
      {open && (
        <div className="pl-4 py-1">
          {node.toolCalls.map((t) => <ToolCallRow key={t.id} entry={t} />)}
          {node.toolCalls.length === 0 && (
            <div className="text-[11px] text-muted-foreground italic px-1">
              {node.status === "running" ? "（运行中…）" : "（无工具调用）"}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
