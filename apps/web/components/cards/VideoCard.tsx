import { parseFileLines } from "./parseFileLines";

export function VideoCard({ body }: { body: string }) {
  const files = parseFileLines(body);
  return (
    <div className="space-y-3 my-3">
      {files.map((f) => (
        <div key={f.path} className="rounded border border-border p-2">
          <div className="text-sm font-medium mb-2">{f.name}</div>
          <video src={`/api/proxy/files/preview?path=${encodeURIComponent(f.path)}`}
                 controls className="w-full rounded" />
        </div>
      ))}
    </div>
  );
}
