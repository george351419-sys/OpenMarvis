import { parseFileLines } from "./parseFileLines";

export function DeleteListCard({ body }: { body: string }) {
  const files = parseFileLines(body);
  return (
    <div className="rounded-md border border-red-500/30 p-3 my-3 bg-red-500/5">
      <div className="text-xs text-red-600 mb-2">已删除（移至回收站，7 天后硬删）</div>
      <ul className="space-y-1">
        {files.map((f) => (
          <li key={f.path} className="font-mono text-sm line-through">{f.path}</li>
        ))}
      </ul>
    </div>
  );
}
