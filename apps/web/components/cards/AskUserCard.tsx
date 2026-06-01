"use client";

import { useState } from "react";

import { api } from "@/lib/api";
import { useChat } from "@/lib/store";

interface Props {
  convId: string;
  ask_id: string;
  title: string;
  form_type: "single_select" | "multi_select" | "confirm";
  options: Array<{ label?: string; description?: string }>;
}

export function AskUserCard({ convId, ask_id, title, form_type, options }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const setAsk = useChat((s) => s.setAsk);

  const toggle = (label: string) => {
    if (form_type === "multi_select") {
      setSelected((s) => s.includes(label) ? s.filter((x) => x !== label) : [...s, label]);
    } else {
      setSelected([label]);
    }
  };

  const submit = async () => {
    await api.answerAsk(convId, ask_id, selected.length ? selected : ["cancel"]);
    setAsk(null);
  };

  return (
    <div className="rounded-md border border-amber-500/40 p-4 my-3 bg-amber-50 dark:bg-amber-900/20">
      <div className="font-medium mb-3">{title}</div>
      <div className="flex flex-wrap gap-2">
        {options.map((o, i) => (
          <button key={i}
                  className={`px-3 py-1 rounded border text-sm ${
                    selected.includes(o.label ?? "")
                      ? "bg-amber-200 border-amber-500"
                      : "bg-white border-border hover:bg-muted"}`}
                  onClick={() => toggle(o.label ?? `option-${i}`)}>
            {o.label}
            {o.description && <span className="text-xs text-muted-foreground ml-1">— {o.description}</span>}
          </button>
        ))}
      </div>
      <button onClick={submit}
              className="mt-3 px-3 py-1 text-sm rounded bg-amber-600 text-white hover:bg-amber-700">
        提交
      </button>
    </div>
  );
}
