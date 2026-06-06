"use client";

interface AppEntry {
  bundleId: string;
  button?: string;
}

function parseAppLines(body: string): AppEntry[] {
  return body
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const match = line.match(/^\[([^\]]+)\](?:\{button=([^}]+)\})?$/);
      if (!match) return null;
      return { bundleId: match[1], button: match[2] };
    })
    .filter((e): e is AppEntry => e !== null);
}

export function AppListCard({ body }: { body: string }) {
  const apps = parseAppLines(body);

  if (!apps.length) {
    return (
      <div className="rounded-md border border-border p-3 my-3 bg-muted/40 font-mono text-xs whitespace-pre-wrap">
        {body.trim()}
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border p-3 my-3">
      <div className="text-xs text-muted-foreground mb-2 font-medium">应用列表</div>
      <div className="flex flex-col gap-2">
        {apps.map((app, i) => (
          <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded bg-muted/40 hover:bg-muted/70 transition-colors">
            <span className="text-sm font-mono text-foreground">{app.bundleId}</span>
            {app.button && (
              <span className="text-xs px-2 py-0.5 rounded bg-blue-500/20 text-blue-600 dark:text-blue-400 border border-blue-500/30">
                {app.button}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
