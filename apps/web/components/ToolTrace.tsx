"use client";

import { useState } from "react";
import { ChevronRight, Loader2, CheckCircle2, XCircle } from "lucide-react";

import type { ToolTrace as T } from "@/lib/store";

export function ToolTrace({ tools }: { tools: T[] }) {
  const [open, setOpen] = useState(false);
  if (tools.length === 0) return null;
  return (
    <div className="my-2 text-xs">
      <button onClick={() => setOpen((v) => !v)}
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
        <ChevronRight className={`w-3 h-3 transition-transform ${open ? "rotate-90" : ""}`} />
        工具调用 ({tools.length})
      </button>
      {open && (
        <ul className="mt-1 space-y-1">
          {tools.map((t) => (
            <li key={t.call_id} className="flex items-start gap-2 font-mono">
              {t.ok === undefined ? <Loader2 className="w-3 h-3 animate-spin mt-0.5" />
                : t.ok ? <CheckCircle2 className="w-3 h-3 text-emerald-600 mt-0.5" />
                : <XCircle className="w-3 h-3 text-red-600 mt-0.5" />}
              <div>
                <span className="font-semibold">{t.name}</span>
                <span className="text-muted-foreground"> {JSON.stringify(t.args)}</span>
                {t.preview && <div className="text-muted-foreground">{t.preview}</div>}
                {t.error && <div className="text-red-600">{t.error}</div>}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
