"use client";
import { useState } from "react";
import { ChevronRight } from "lucide-react";

export function ThinkingPane({ text }: { text: string }) {
  const [open, setOpen] = useState(false);
  if (!text) return null;
  return (
    <div className="my-2 text-xs">
      <button onClick={() => setOpen((v) => !v)}
              className="text-muted-foreground hover:text-foreground inline-flex items-center gap-1">
        <ChevronRight className={`w-3 h-3 transition-transform ${open ? "rotate-90" : ""}`} />
        thinking
      </button>
      {open && (
        <pre className="mt-1 bg-muted p-2 rounded whitespace-pre-wrap font-mono">{text}</pre>
      )}
    </div>
  );
}
