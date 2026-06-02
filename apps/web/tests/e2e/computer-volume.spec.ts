import { test, expect } from "@playwright/test";

test.skip(!process.env.OPENMARVIS_E2E_LIVE, "需要 ANTHROPIC_API_KEY + OPENMARVIS_E2E_LIVE=1");

test("computer-agent: read current volume", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL(/\/c\//);

  const textarea = page.locator("textarea");
  await textarea.fill("用 Computer Agent 读取当前系统音量是多少");
  await page.keyboard.press("Meta+Enter");

  await expect(page.getByText(/\b\d{1,3}\b/)).toBeVisible({ timeout: 60_000 });
});
