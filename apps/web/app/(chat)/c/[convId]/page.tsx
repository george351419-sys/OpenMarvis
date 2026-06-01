import { ChatStream } from "@/components/ChatStream";
import { ConversationSidebar } from "@/components/ConversationSidebar";

export default function ConvPage({ params }: { params: { convId: string } }) {
  return (
    <div className="flex h-screen">
      <ConversationSidebar activeId={params.convId} />
      <main className="flex-1">
        <ChatStream convId={params.convId} />
      </main>
    </div>
  );
}
