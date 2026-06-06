import { MarkdownRenderer } from "./MarkdownRenderer";
import { ThinkingPane } from "./ThinkingPane";
import { ToolTrace } from "./ToolTrace";
import { CARD_RENDERERS } from "./cards";
import type { CardKey } from "./cards";
import type { AssistantTurn } from "@/lib/store";

interface UserBubble { role: "user"; text: string }
interface AssistantBubble { role: "assistant"; turn: AssistantTurn; convId: string }
type Props = UserBubble | AssistantBubble;

export function MessageBubble(props: Props) {
  if (props.role === "user") {
    return (
      <div className="flex justify-end my-3">
        <div className="max-w-[75%] bg-foreground text-background rounded-2xl px-4 py-2 whitespace-pre-wrap">
          {props.text}
        </div>
      </div>
    );
  }
  const { turn, convId } = props;
  return (
    <div className="flex justify-start my-3">
      <div className="max-w-[85%] w-full">
        <ThinkingPane text={turn.thinking} />
        <ToolTrace tools={turn.tools} />
        <MarkdownRenderer>{turn.content}</MarkdownRenderer>
        {turn.cards.map((c, i) => {
          const Renderer = CARD_RENDERERS[c.type as CardKey] as any;
          if (!Renderer) return null;
          if (c.type === "mv-ask-user" || c.type === "deletion_preview") {
            try {
              const data = JSON.parse(c.payload);
              return <Renderer key={i} convId={convId} {...data} />;
            } catch { return null; }
          }
          return <Renderer key={i} body={c.payload} />;
        })}
        {turn.error && (
          <div className="mt-2 border border-red-200 bg-red-50 rounded px-3 py-2
                            text-sm text-red-700 whitespace-pre-wrap break-all">
            ⚠️ 错误：{turn.error}
          </div>
        )}
      </div>
    </div>
  );
}
