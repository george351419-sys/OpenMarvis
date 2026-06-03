import { defineConfig } from "@playwright/test";

// v1.0 起统一 OPENMARVIS_LIVE 这一个变量名（跟 backend tests/integration/
// 一致）。OPENMARVIS_E2E_LIVE 保留作为 deprecated alias，spec 文件里现有
// 的 test.skip(!process.env.OPENMARVIS_E2E_LIVE, …) 不动。
if (process.env.OPENMARVIS_LIVE === "1" && !process.env.OPENMARVIS_E2E_LIVE) {
  process.env.OPENMARVIS_E2E_LIVE = "1";
}

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 120_000,
  fullyParallel: false,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:3000",
    headless: true,
    trace: "retain-on-failure",
  },
  webServer: [
    {
      command: "cd ../backend && .venv/bin/uvicorn openmarvis.main:app --port 8001",
      port: 8001, reuseExistingServer: true, timeout: 30_000,
    },
    {
      command: "pnpm dev",
      port: 3000, reuseExistingServer: true, timeout: 30_000,
    },
  ],
});
