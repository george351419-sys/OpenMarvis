import { defineConfig } from "@playwright/test";

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
