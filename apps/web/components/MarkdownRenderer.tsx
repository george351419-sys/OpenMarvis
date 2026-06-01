import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { CARD_RENDERERS, CardKey } from "./cards";

export function MarkdownRenderer({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        code({ className, children, ...props }) {
          const lang = /language-(\S+)/.exec(className ?? "")?.[1] as CardKey | undefined;
          const text = String(children).replace(/\n$/, "");
          if (lang && lang in CARD_RENDERERS) {
            const Renderer = CARD_RENDERERS[lang] as any;
            return <Renderer body={text} />;
          }
          return (
            <code className={`bg-muted px-1 rounded text-sm ${className ?? ""}`} {...props as any}>
              {children}
            </code>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
