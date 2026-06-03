import { useState } from "react";
import { ChevronRight } from "lucide-react";

import { ToolCallEntry } from "@/lib/stores/timeline";
import { DurationLabel } from "./DurationLabel";
import { RiskBadge } from "./RiskBadge";

export function ToolCallRow({ entry }: { entry: ToolCallEntry }) {
  const [open, setOpen] = useState(false);
  const dot =
    entry.status === "running" ? "bg-blue-500 animate-pulse" :
    entry.status === "ok"      ? "bg-emerald-500" :
                                    "bg-red-500";
  return (
    <div className="text-xs">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 py-1 hover:bg-muted/50 rounded px-1"
      >
        <ChevronRight className={`w-3 h-3 transition-transform
                                     ${open ? "rotate-90" : ""}`} />
        <span className={`inline-block w-1.5 h-1.5 rounded-full ${dot}`} />
        <span className="font-mono truncate flex-1 text-left">
          {entry.toolName}
        </span>
        <RiskBadge level={entry.riskLevel} />
        <DurationLabel startedAt={entry.startedAt} endedAt={entry.endedAt} />
      </button>
      {open && (
        <div className="ml-7 mb-1 mt-0.5 text-[11px] text-muted-foreground
                          whitespace-pre-wrap break-all">
          <div><b>args:</b> {entry.argsPreview}</div>
          {entry.errorMessage && (
            <div className="text-red-600"><b>error:</b> {entry.errorMessage}</div>
          )}
        </div>
      )}
    </div>
  );
}
