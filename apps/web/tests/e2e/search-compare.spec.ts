import { test, expect } from "@playwright/test";

test.skip(!process.env.OPENMARVIS_E2E_LIVE, "需要联网 + 真实 LLM");

test("compare X vs Y → Search Agent produces table", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL(/\/c\//);
  const textarea = page.locator("textarea");
  await textarea.fill("对比 FastAPI 与 Flask 的差异，输出表格");
  await page.keyboard.press("Meta+Enter");
  await expect(page.locator("table")).toBeVisible({ timeout: 60_000 });
});
