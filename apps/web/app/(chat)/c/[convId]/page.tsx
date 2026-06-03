import { ChatStream } from "@/components/ChatStream";
import { ConversationSidebar } from "@/components/ConversationSidebar";
import { TimelinePanel } from "@/components/timeline/TimelinePanel";

export default function ConvPage({ params }: { params: { convId: string } }) {
  return (
    <div className="flex h-screen">
      <ConversationSidebar activeId={params.convId} />
      <main className="flex-1 min-w-0">
        <ChatStream convId={params.convId} />
      </main>
      <TimelinePanel />
    </div>
  );
}
