"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function SettingsPage() {
  const [data, setData] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  useEffect(() => { api.getSettings().then(setData); }, []);
  if (!data) return <div className="p-6">加载中...</div>;
  const save = async () => {
    setSaving(true);
    try { setData(await api.putSettings({ llm: data.llm, security: data.security })); }
    finally { setSaving(false); }
  };
  return (
    <div className="max-w-2xl mx-auto p-6 space-y-6">
      <h1 className="text-xl font-semibold">设置</h1>
      <section className="space-y-2">
        <h2 className="font-medium">LLM</h2>
        <label className="flex items-center gap-3">
          <span className="w-32 text-sm">模型</span>
          <input className="flex-1 rounded border border-border p-1 text-sm"
                 value={data.llm.provider_model}
                 onChange={(e) => setData({ ...data, llm: { ...data.llm, provider_model: e.target.value } })} />
        </label>
        <label className="flex items-center gap-3">
          <span className="w-32 text-sm">temperature</span>
          <input type="number" step="0.1" className="rounded border border-border p-1 text-sm w-32"
                 value={data.llm.temperature}
                 onChange={(e) => setData({ ...data, llm: { ...data.llm, temperature: Number(e.target.value) } })} />
        </label>
      </section>
      <section className="space-y-2">
        <h2 className="font-medium">安全</h2>
        <label className="flex items-center gap-3">
          <span className="w-32 text-sm">等级</span>
          <select className="rounded border border-border p-1 text-sm"
                  value={data.security.level}
                  onChange={(e) => setData({ ...data, security: { ...data.security, level: e.target.value } })}>
            <option value="strict">strict</option>
            <option value="normal">normal</option>
            <option value="permissive">permissive</option>
          </select>
        </label>
      </section>
      <button onClick={save} disabled={saving}
              className="px-4 py-1 rounded bg-foreground text-background text-sm hover:opacity-90 disabled:opacity-40">
        {saving ? "保存中..." : "保存"}
      </button>
    </div>
  );
}
