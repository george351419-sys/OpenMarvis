"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft, Sparkles } from "lucide-react";

import { api, SkillDTO } from "@/lib/api";

function riskBadge(risk: SkillDTO["risk"]) {
  const cls =
    risk === "high"   ? "bg-red-100 text-red-700"   :
    risk === "medium" ? "bg-amber-100 text-amber-700" :
                          "bg-emerald-100 text-emerald-700";
  return (
    <span className={`text-[10px] px-1.5 py-0.5 rounded ${cls}`}>{risk}</span>
  );
}

export default function SkillsPage() {
  const [items, setItems] = useState<SkillDTO[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.listSkills().then(setItems).catch((e) => setError(String(e)));
  }, []);

  return (
    <div className="max-w-3xl mx-auto p-6">
      <div className="flex items-center justify-between mb-4">
        <Link href="/" className="text-sm text-muted-foreground hover:underline
                                    inline-flex items-center gap-1">
          <ArrowLeft className="w-4 h-4" /> 返回
        </Link>
        <h1 className="text-lg font-semibold inline-flex items-center gap-2">
          <Sparkles className="w-4 h-4" /> Skills
        </h1>
        <span />
      </div>

      <p className="text-xs text-muted-foreground mb-4">
        Skill 把固定工作流（如格式转换、报表生成）封装成可在聊天里直接调用的能力。
        放置目录：<code className="bg-muted px-1 rounded">~/.openmarvis/skills/</code>
      </p>

      {error && (
        <div className="mb-3 text-sm text-red-600 border border-red-200 rounded px-3 py-2">
          {error}
        </div>
      )}

      {items === null ? (
        <div className="text-sm text-muted-foreground">加载中…</div>
      ) : items.length === 0 ? (
        <div className="text-sm text-muted-foreground border border-dashed
                          border-border rounded p-6 text-center">
          没有已安装 Skill。在 <code>~/.openmarvis/skills/&lt;name&gt;/skill.yaml</code> 放一个。
        </div>
      ) : (
        <ul className="space-y-2">
          {items.map((s) => (
            <li key={s.name} className="border border-border rounded p-3">
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium">{s.name}</span>
                    <span className="text-xs text-muted-foreground">
                      v{s.version}
                    </span>
                    {riskBadge(s.risk)}
                  </div>
                  <div className="text-xs mt-1 whitespace-pre-wrap">
                    {s.description || "(无描述)"}
                  </div>
                  {Object.keys(s.params).length > 0 && (
                    <details className="mt-2">
                      <summary className="text-xs cursor-pointer text-muted-foreground
                                            hover:underline">
                        参数（{Object.keys(s.params).length}）
                      </summary>
                      <ul className="mt-1 ml-3 text-xs space-y-0.5">
                        {Object.entries(s.params).map(([name, p]) => (
                          <li key={name}>
                            <code>{name}</code>
                            <span className="text-muted-foreground">
                              {" "}: {p.type}
                              {p.required ? " (required)" : ""}
                              {p.enum ? ` ∈ {${p.enum.join(", ")}}` : ""}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </details>
                  )}
                  <div className="text-xs text-muted-foreground mt-1">
                    允许工具：{s.allowed_tools.join(", ") || "—"}
                  </div>
                </div>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
