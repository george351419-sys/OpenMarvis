"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

interface HealthStatus {
  overall: "healthy" | "warning" | "error" | "unknown";
  checks: Record<string, { status: string; [key: string]: any }>;
}

interface RuntimeInfo {
  llm: {
    provider_model: string;
    api_base: string | null;
    vision_model: string;
    max_tokens: number;
    temperature: number;
    key_presence: {
      any_present: boolean | null;
      present_env: string | null;
      validation?: { valid: boolean; reason?: string; expected?: string };
      key_prefix?: string;
    };
    vision_key_presence: {
      any_present: boolean | null;
      present_env: string | null;
    };
  };
  workspace: {
    root: string;
    diagnosis: {
      exists: boolean;
      readable?: boolean;
      writable?: boolean;
      disk?: {
        total_gb: number;
        used_gb: number;
        free_gb: number;
        usage_pct: number;
      };
      current_size_mb?: number;
      can_create?: boolean;
    };
    limits: {
      max_total_gb: number;
      max_per_conv_mb: number;
      warn_threshold_pct: number;
    };
  };
  version: string;
}

function StatusBadge({ status }: { status: string }) {
  const colors = {
    ok: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    healthy: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
    warning: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
    error: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
    unknown: "bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200",
  };
  return (
    <span className={`px-2 py-0.5 rounded text-xs font-medium ${colors[status as keyof typeof colors] || colors.unknown}`}>
      {status}
    </span>
  );
}

export default function SettingsPage() {
  const [data, setData] = useState<any>(null);
  const [info, setInfo] = useState<RuntimeInfo | null>(null);
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [configPath, setConfigPath] = useState<any>(null);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [reloading, setReloading] = useState(false);
  const [testResult, setTestResult] = useState<any>(null);
  const [activeTab, setActiveTab] = useState<"config" | "diagnostics">("config");

  useEffect(() => {
    Promise.all([
      api.getSettings(),
      api.getSettingsInfo(),
      api.getSettingsHealth(),
      api.getConfigPath(),
    ]).then(([settings, runtimeInfo, healthStatus, configPathInfo]) => {
      setData(settings);
      setInfo(runtimeInfo);
      setHealth(healthStatus);
      setConfigPath(configPathInfo);
    });
  }, []);

  if (!data || !info || !health) return <div className="p-6">加载中...</div>;

  const save = async () => {
    setSaving(true);
    try {
      const updated = await api.putSettings({ llm: data.llm, security: data.security });
      setData(updated);
      // 重新获取诊断信息
      const [newInfo, newHealth] = await Promise.all([
        api.getSettingsInfo(),
        api.getSettingsHealth(),
      ]);
      setInfo(newInfo);
      setHealth(newHealth);
      alert("配置已保存到文件");
    } finally {
      setSaving(false);
    }
  };

  const testConnection = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const result = await api.testApiConnection();
      setTestResult(result);
    } catch (error: any) {
      setTestResult({
        status: "error",
        error: error.message || "测试失败",
      });
    } finally {
      setTesting(false);
    }
  };

  const reloadConfigFromFile = async () => {
    setReloading(true);
    try {
      const result = await api.reloadConfig();
      if (result.ok) {
        // 重新加载所有数据
        const [settings, runtimeInfo, healthStatus] = await Promise.all([
          api.getSettings(),
          api.getSettingsInfo(),
          api.getSettingsHealth(),
        ]);
        setData(settings);
        setInfo(runtimeInfo);
        setHealth(healthStatus);
        alert("配置已从文件重新加载");
      } else {
        alert(result.message || "重载失败");
      }
    } catch (error: any) {
      alert(`重载失败: ${error.message}`);
    } finally {
      setReloading(false);
    }
  };

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">设置</h1>
        <div className="flex items-center gap-2">
          <span className="text-sm text-muted-foreground">系统状态:</span>
          <StatusBadge status={health.overall} />
        </div>
      </div>

      {/* Tab Navigation */}
      <div className="flex gap-1 border-b border-border">
        <button
          onClick={() => setActiveTab("config")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "config"
              ? "border-foreground text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          配置
        </button>
        <button
          onClick={() => setActiveTab("diagnostics")}
          className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
            activeTab === "diagnostics"
              ? "border-foreground text-foreground"
              : "border-transparent text-muted-foreground hover:text-foreground"
          }`}
        >
          诊断信息
        </button>
      </div>

      {activeTab === "config" && (
        <div className="space-y-6">
          <section className="space-y-3 p-4 border border-border rounded-lg">
            <h2 className="font-semibold text-lg">LLM 配置</h2>
            <label className="flex items-center gap-3">
              <span className="w-32 text-sm text-muted-foreground">主模型</span>
              <input
                className="flex-1 rounded border border-border p-2 text-sm bg-background"
                value={data.llm.provider_model}
                onChange={(e) => setData({ ...data, llm: { ...data.llm, provider_model: e.target.value } })}
              />
            </label>
            <label className="flex items-center gap-3">
              <span className="w-32 text-sm text-muted-foreground">API Base</span>
              <input
                className="flex-1 rounded border border-border p-2 text-sm bg-background"
                value={data.llm.api_base || ""}
                onChange={(e) => setData({ ...data, llm: { ...data.llm, api_base: e.target.value || null } })}
                placeholder="留空使用默认"
              />
            </label>
            <label className="flex items-center gap-3">
              <span className="w-32 text-sm text-muted-foreground">视觉模型</span>
              <input
                className="flex-1 rounded border border-border p-2 text-sm bg-background"
                value={data.llm.vision_model}
                onChange={(e) => setData({ ...data, llm: { ...data.llm, vision_model: e.target.value } })}
              />
            </label>
            <label className="flex items-center gap-3">
              <span className="w-32 text-sm text-muted-foreground">Max Tokens</span>
              <input
                type="number"
                className="rounded border border-border p-2 text-sm w-32 bg-background"
                value={data.llm.max_tokens}
                onChange={(e) => setData({ ...data, llm: { ...data.llm, max_tokens: Number(e.target.value) } })}
              />
            </label>
            <label className="flex items-center gap-3">
              <span className="w-32 text-sm text-muted-foreground">Temperature</span>
              <input
                type="number"
                step="0.1"
                className="rounded border border-border p-2 text-sm w-32 bg-background"
                value={data.llm.temperature}
                onChange={(e) => setData({ ...data, llm: { ...data.llm, temperature: Number(e.target.value) } })}
              />
            </label>
          </section>

          <section className="space-y-3 p-4 border border-border rounded-lg">
            <h2 className="font-semibold text-lg">安全设置</h2>
            <label className="flex items-center gap-3">
              <span className="w-32 text-sm text-muted-foreground">安全等级</span>
              <select
                className="rounded border border-border p-2 text-sm bg-background"
                value={data.security.level}
                onChange={(e) => setData({ ...data, security: { ...data.security, level: e.target.value } })}
              >
                <option value="strict">Strict</option>
                <option value="normal">Normal</option>
                <option value="permissive">Permissive</option>
              </select>
            </label>
            <label className="flex items-center gap-3">
              <span className="w-32 text-sm text-muted-foreground">允许 sudo</span>
              <input
                type="checkbox"
                checked={data.security.allow_sudo}
                onChange={(e) => setData({ ...data, security: { ...data.security, allow_sudo: e.target.checked } })}
                className="w-4 h-4"
              />
            </label>
          </section>

          <button
            onClick={save}
            disabled={saving}
            className="px-6 py-2 rounded bg-foreground text-background text-sm font-medium hover:opacity-90 disabled:opacity-40 transition-opacity"
          >
            {saving ? "保存中..." : "保存配置"}
          </button>
        </div>
      )}

      {activeTab === "diagnostics" && (
        <div className="space-y-6">
          {/* Health Overview */}
          <section className="p-4 border border-border rounded-lg space-y-3">
            <h2 className="font-semibold text-lg">健康检查</h2>
            <div className="space-y-2">
              {Object.entries(health.checks).map(([key, check]) => (
                <div key={key} className="flex items-center justify-between p-2 bg-muted/30 rounded">
                  <span className="text-sm font-medium">{key}</span>
                  <StatusBadge status={check.status} />
                </div>
              ))}
            </div>
          </section>

          {/* API Key Status */}
          <section className="p-4 border border-border rounded-lg space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-lg">API Key 状态</h2>
              <button
                onClick={testConnection}
                disabled={testing}
                className="px-3 py-1 text-xs rounded border border-border hover:bg-muted disabled:opacity-40 transition-colors"
              >
                {testing ? "测试中..." : "测试连接"}
              </button>
            </div>

            {testResult && (
              <div
                className={`p-3 rounded text-sm ${
                  testResult.status === "ok"
                    ? "bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800"
                    : "bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800"
                }`}
              >
                {testResult.status === "ok" ? (
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-green-800 dark:text-green-200">✓ 连接成功</span>
                    </div>
                    <div className="text-xs text-green-700 dark:text-green-300">
                      延迟: {testResult.latency_ms}ms
                    </div>
                    {testResult.response_preview && (
                      <div className="text-xs text-green-600 dark:text-green-400">
                        响应预览: {testResult.response_preview}
                      </div>
                    )}
                  </div>
                ) : (
                  <div>
                    <div className="font-medium text-red-800 dark:text-red-200">✗ 连接失败</div>
                    <div className="text-xs text-red-700 dark:text-red-300 mt-1">
                      {testResult.error}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <div className="text-sm font-medium mb-1">主模型: {info.llm.provider_model}</div>
                {info.llm.key_presence.any_present ? (
                  <div className="text-sm space-y-1">
                    <div className="flex items-center gap-2">
                      <StatusBadge status="ok" />
                      <span className="text-muted-foreground">
                        环境变量: {info.llm.key_presence.present_env}
                      </span>
                    </div>
                    {info.llm.key_presence.key_prefix && (
                      <div className="text-xs text-muted-foreground">
                        Key 前缀: {info.llm.key_presence.key_prefix}
                      </div>
                    )}
                    {info.llm.key_presence.validation && (
                      <div className="flex items-center gap-2">
                        {info.llm.key_presence.validation.valid ? (
                          <>
                            <StatusBadge status="ok" />
                            <span className="text-xs text-muted-foreground">格式验证通过</span>
                          </>
                        ) : (
                          <>
                            <StatusBadge status="error" />
                            <span className="text-xs text-muted-foreground">
                              格式错误: {info.llm.key_presence.validation.reason}
                              {info.llm.key_presence.validation.expected && ` (期望: ${info.llm.key_presence.validation.expected})`}
                            </span>
                          </>
                        )}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <StatusBadge status="error" />
                    <span className="text-sm text-muted-foreground">未找到 API Key</span>
                  </div>
                )}
              </div>

              <div>
                <div className="text-sm font-medium mb-1">视觉模型: {info.llm.vision_model}</div>
                {info.llm.vision_key_presence.any_present ? (
                  <div className="flex items-center gap-2">
                    <StatusBadge status="ok" />
                    <span className="text-sm text-muted-foreground">
                      环境变量: {info.llm.vision_key_presence.present_env}
                    </span>
                  </div>
                ) : (
                  <div className="flex items-center gap-2">
                    <StatusBadge status="warning" />
                    <span className="text-sm text-muted-foreground">未找到 API Key</span>
                  </div>
                )}
              </div>
            </div>
          </section>

          {/* Workspace Status */}
          <section className="p-4 border border-border rounded-lg space-y-3">
            <h2 className="font-semibold text-lg">工作空间</h2>
            <div className="space-y-2 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-muted-foreground">路径:</span>
                <code className="text-xs bg-muted px-2 py-1 rounded">{info.workspace.root}</code>
              </div>
              {info.workspace.diagnosis.exists ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">状态:</span>
                    <div className="flex items-center gap-2">
                      {info.workspace.diagnosis.readable && <span className="text-xs">✓ 可读</span>}
                      {info.workspace.diagnosis.writable && <span className="text-xs">✓ 可写</span>}
                    </div>
                  </div>
                  {info.workspace.diagnosis.disk && (
                    <div className="space-y-1">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">磁盘空间:</span>
                        <span className="text-xs">
                          {info.workspace.diagnosis.disk.free_gb.toFixed(2)} GB 可用 / {info.workspace.diagnosis.disk.total_gb.toFixed(2)} GB 总计
                        </span>
                      </div>
                      <div className="w-full bg-muted rounded-full h-2">
                        <div
                          className={`h-2 rounded-full ${
                            info.workspace.diagnosis.disk.usage_pct > 90
                              ? "bg-red-500"
                              : info.workspace.diagnosis.disk.usage_pct > 80
                              ? "bg-yellow-500"
                              : "bg-green-500"
                          }`}
                          style={{ width: `${info.workspace.diagnosis.disk.usage_pct}%` }}
                        />
                      </div>
                      <div className="text-xs text-muted-foreground text-right">
                        使用率: {info.workspace.diagnosis.disk.usage_pct}%
                      </div>
                    </div>
                  )}
                  {info.workspace.diagnosis.current_size_mb !== undefined && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">当前大小:</span>
                      <span className="text-xs">
                        {info.workspace.diagnosis.current_size_mb.toFixed(2)} MB / {info.workspace.limits.max_total_gb * 1024} MB 限制
                      </span>
                    </div>
                  )}
                </>
              ) : (
                <div className="flex items-center gap-2">
                  <StatusBadge status="warning" />
                  <span className="text-muted-foreground">
                    目录不存在 {info.workspace.diagnosis.can_create && "(可创建)"}
                  </span>
                </div>
              )}
            </div>
          </section>

          {/* Version Info */}
          <section className="p-4 border border-border rounded-lg">
            <div className="flex items-center justify-between">
              <h2 className="font-semibold text-lg">版本信息</h2>
              <span className="text-sm text-muted-foreground">{info.version}</span>
            </div>
          </section>

          {/* Config File Info */}
          {configPath && (
            <section className="p-4 border border-border rounded-lg space-y-3">
              <div className="flex items-center justify-between">
                <h2 className="font-semibold text-lg">配置文件</h2>
                <button
                  onClick={reloadConfigFromFile}
                  disabled={reloading || !configPath.exists}
                  className="px-3 py-1 text-xs rounded border border-border hover:bg-muted disabled:opacity-40 transition-colors"
                >
                  {reloading ? "重载中..." : "从文件重载"}
                </button>
              </div>
              <div className="space-y-2 text-sm">
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">路径:</span>
                  <code className="text-xs bg-muted px-2 py-1 rounded">{configPath.path}</code>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-muted-foreground">状态:</span>
                  <div className="flex items-center gap-2">
                    {configPath.exists ? (
                      <StatusBadge status="ok" />
                    ) : (
                      <StatusBadge status="warning" />
                    )}
                    <span className="text-xs">
                      {configPath.exists ? "文件存在" : "文件不存在"}
                    </span>
                  </div>
                </div>
                {!configPath.exists && configPath.writable && (
                  <div className="text-xs text-muted-foreground">
                    💡 保存配置后将自动创建配置文件
                  </div>
                )}
              </div>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
