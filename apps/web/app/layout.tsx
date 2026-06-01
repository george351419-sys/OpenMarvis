import "./globals.css";

import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "OpenMarvis",
  description: "Open-source Marvis-like desktop AI agent",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN">
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
