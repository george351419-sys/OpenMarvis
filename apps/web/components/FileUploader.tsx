"use client";
import { useState } from "react";
import { Upload } from "lucide-react";

import { api } from "@/lib/api";

interface Props { convId: string; onUploaded: (paths: string[]) => void }

export function FileUploader({ convId, onUploaded }: Props) {
  const [busy, setBusy] = useState(false);
  return (
    <label className={`inline-flex items-center gap-1 px-2 py-1 rounded cursor-pointer
                       border border-border hover:bg-muted text-sm
                       ${busy ? "opacity-50 pointer-events-none" : ""}`}>
      <Upload className="w-3 h-3" />
      上传
      <input type="file" multiple className="hidden"
             onChange={async (e) => {
               const files = Array.from(e.target.files ?? []);
               if (files.length === 0) return;
               setBusy(true);
               try {
                 const paths: string[] = [];
                 for (const f of files) {
                   const out = await api.upload(convId, f);
                   paths.push(...out.map((x) => x.saved_path));
                 }
                 onUploaded(paths);
               } finally { setBusy(false); }
             }} />
    </label>
  );
}
