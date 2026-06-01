"use client";

import { useEffect, useState } from "react";
import { openSSE } from "@/lib/sse";

export default function EchoPage() {
  const [chars, setChars] = useState<string[]>([]);
  const [done, setDone] = useState(false);

  useEffect(() => {
    const close = openSSE("/echo?message=hello%20openmarvis", {
      onEvent: (_evt, data: any) => {
        if (data?.char) setChars((c) => [...c, data.char]);
        if (data?.done) setDone(true);
      },
    });
    return close;
  }, []);

  return (
    <main className="min-h-screen flex flex-col items-center justify-center gap-2 p-8">
      <h1 className="text-2xl font-semibold">SSE Echo</h1>
      <p className="font-mono text-xl">{chars.join("")}</p>
      <p className="text-muted-foreground">{done ? "done" : "streaming..."}</p>
    </main>
  );
}
