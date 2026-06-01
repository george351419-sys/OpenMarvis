"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { api, ConversationDTO } from "@/lib/api";
import { ConversationSidebar } from "@/components/ConversationSidebar";

export default function HomePage() {
  const router = useRouter();
  const [convs, setConvs] = useState<ConversationDTO[]>([]);

  useEffect(() => {
    api.listConversations().then(async (rows) => {
      if (rows.length === 0) {
        const c = await api.createConversation("");
        router.replace(`/c/${c.id}`);
      } else {
        setConvs(rows);
        router.replace(`/c/${rows[0].id}`);
      }
    });
  }, [router]);

  return (
    <div className="flex h-screen">
      <ConversationSidebar />
      <main className="flex-1 flex items-center justify-center text-muted-foreground">
        正在打开会话…
      </main>
    </div>
  );
}
