import { test, expect } from "@playwright/test";

test.skip(!process.env.OPENMARVIS_E2E_LIVE, "需要 ANTHROPIC_API_KEY + OPENMARVIS_E2E_LIVE=1");

test("browser-agent: open example.com and report h1 text", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL(/\/c\//);

  const textarea = page.locator("textarea");
  await textarea.fill("用 Browser Agent 打开 https://example.com，然后告诉我 h1 文本");
  await page.keyboard.press("Meta+Enter");

  await expect(page.getByText("Example Domain")).toBeVisible({ timeout: 120_000 });
});
