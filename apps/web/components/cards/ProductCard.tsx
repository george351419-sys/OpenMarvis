import { parseFileLines } from "./parseFileLines";

export function ProductCard({ body }: { body: string }) {
  const files = parseFileLines(body);
  return (
    <div className="rounded-md border border-emerald-500/30 p-3 my-3 bg-emerald-500/5">
      <div className="text-xs text-emerald-700 font-semibold mb-2">本次产出物</div>
      <ul className="space-y-1">
        {files.map((f) => (
          <li key={f.path} className="font-mono text-sm">
            <a className="underline" target="_blank" rel="noreferrer"
               href={`/api/proxy/files/download?path=${encodeURIComponent(f.path)}`}>{f.name}</a>
            <span className="text-muted-foreground"> — {f.path}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
