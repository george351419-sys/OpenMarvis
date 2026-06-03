import { test, expect } from "@playwright/test";

test.skip(!process.env.OPENMARVIS_E2E_LIVE, "需要 ANTHROPIC_API_KEY + OPENMARVIS_E2E_LIVE=1");

test("write to ~/Desktop triggers PathGuard ask_user", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL(/\/c\//);
  const textarea = page.locator("textarea");
  await textarea.fill("把'hello'写入 ~/Desktop/openmarvis-test.txt");
  await page.keyboard.press("Meta+Enter");
  await expect(page.getByText(/请确认|workspace 外/)).toBeVisible({ timeout: 60_000 });
});
