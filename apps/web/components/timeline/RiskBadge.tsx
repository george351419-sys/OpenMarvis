export function RiskBadge({ level }: { level?: "low" | "medium" | "high" }) {
  if (!level) return null;
  const cls =
    level === "high"   ? "bg-red-100 text-red-700" :
    level === "medium" ? "bg-amber-100 text-amber-700" :
                            "bg-slate-100 text-slate-600";
  return (
    <span className={`text-[10px] px-1 rounded ${cls}`}>{level}</span>
  );
}
