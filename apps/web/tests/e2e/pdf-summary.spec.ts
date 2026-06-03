import { test, expect } from "@playwright/test";
import path from "node:path";

test.skip(!process.env.OPENMARVIS_E2E_LIVE, "需要 ANTHROPIC_API_KEY + OPENMARVIS_E2E_LIVE=1");

test("upload PDF → File Agent summarizes → mv-product appears", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL(/\/c\//, { timeout: 15_000 });

  const input = await page.waitForSelector('input[type="file"]', { state: "attached" });
  await input.setInputFiles(path.join(__dirname, "fixtures/hello.pdf"));

  const textarea = page.locator("textarea");
  await textarea.fill("请阅读这份 PDF 并写一份要点总结，保存为 output/summary.md");
  await page.keyboard.press("Meta+Enter");

  await expect(page.getByText("本次产出物")).toBeVisible({ timeout: 90_000 });
});
