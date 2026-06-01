import { parseFileLines } from "./parseFileLines";

export function FileListCard({ body }: { body: string }) {
  const files = parseFileLines(body);
  if (files.length === 0) return null;
  return (
    <div className="rounded-md border border-border p-3 my-3 bg-muted/40">
      <div className="text-xs text-muted-foreground mb-2">文件列表</div>
      <ul className="space-y-1">
        {files.map((f) => (
          <li key={f.path} className="font-mono text-sm">
            <a className="underline" target="_blank" rel="noreferrer"
               href={`/api/proxy/files/preview?path=${encodeURIComponent(f.path)}`}>{f.name}</a>
            <span className="text-muted-foreground"> — {f.path}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
