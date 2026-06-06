interface ToolCallPayload {
  tool_call_id?: string;
  description?: string;
  status?: string;
  trigger?: string;
  next_run?: string;
}

export function ToolCallCard({ body }: { body: string }) {
  let parsed: ToolCallPayload | null = null;
  try {
    parsed = JSON.parse(body);
  } catch {
    // not JSON — render raw
  }

  if (parsed) {
    return (
      <div className="rounded-md border border-blue-500/30 p-3 my-3 bg-blue-500/5">
        <div className="text-xs text-blue-600 dark:text-blue-400 mb-1.5 font-medium">
          {parsed.description ?? "工具操作"}
        </div>
        {parsed.status && (
          <div className="text-xs text-muted-foreground mb-1">
            状态：{parsed.status}
          </div>
        )}
        {parsed.trigger && (
          <div className="text-xs text-muted-foreground mb-1">
            触发：{parsed.trigger}
          </div>
        )}
        {parsed.next_run && (
          <div className="text-xs text-muted-foreground">
            下次执行：{parsed.next_run}
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="rounded-md border border-border p-3 my-3 bg-muted/40 font-mono text-xs whitespace-pre-wrap">
      <div className="text-muted-foreground mb-1 font-sans">工具操作结果</div>
      {body.trim()}
    </div>
  );
}
