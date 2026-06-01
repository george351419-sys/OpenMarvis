import { parseFileLines } from "./parseFileLines";

export function ImageGalleryCard({ body }: { body: string }) {
  const files = parseFileLines(body);
  return (
    <div className="grid grid-cols-3 gap-2 my-3">
      {files.map((f) => (
        <a key={f.path} href={`/api/proxy/files/preview?path=${encodeURIComponent(f.path)}`}
           target="_blank" rel="noreferrer"
           className="block aspect-square overflow-hidden rounded border border-border">
          <img src={`/api/proxy/files/preview?path=${encodeURIComponent(f.path)}`}
               alt={f.name} className="w-full h-full object-cover" />
        </a>
      ))}
    </div>
  );
}
