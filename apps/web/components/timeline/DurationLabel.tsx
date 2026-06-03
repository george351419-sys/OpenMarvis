export function DurationLabel({ startedAt, endedAt }:
    { startedAt: number; endedAt?: number }) {
  const ms = (endedAt ?? Date.now()) - startedAt;
  let label: string;
  if (ms < 1000) label = `${ms}ms`;
  else if (ms < 60_000) label = `${(ms / 1000).toFixed(1)}s`;
  else label = `${Math.floor(ms / 60_000)}m${Math.floor((ms % 60_000) / 1000)}s`;
  return <span className="text-[11px] text-muted-foreground">{label}</span>;
}
