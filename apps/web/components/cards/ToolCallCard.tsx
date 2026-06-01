export function ToolCallCard({ body }: { body: string }) {
  return (
    <div className="rounded-md border border-border p-3 my-3 bg-muted/40 font-mono text-xs">
      <div className="text-muted-foreground mb-1">工具操作结果</div>
      {body.trim()}
    </div>
  );
}
