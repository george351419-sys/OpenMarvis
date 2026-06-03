import { Sparkles } from "lucide-react";

export function SkillCallCard({ body }: { body: string }) {
  // body 形如 "document_convert → ok" 或 "document_convert → failed"
  const [name, status] = body.split(" → ").map((s) => s.trim());
  const ok = status === "ok";
  return (
    <div className="rounded-md border border-border my-3 px-3 py-2
                      bg-amber-50/40 text-xs flex items-center gap-2">
      <Sparkles className="w-3.5 h-3.5 text-amber-700" />
      <span className="font-medium">{name || "skill"}</span>
      <span className={`ml-auto text-[11px] ${ok ? "text-emerald-700" : "text-red-700"}`}>
        {status || "—"}
      </span>
    </div>
  );
}
