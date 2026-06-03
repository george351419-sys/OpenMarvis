import { expect, test } from "@playwright/test";

// Non-live: 内置 document_convert skill 启动时被扫描，前端从 /skills 拉。

test("skills page: lists builtin document_convert", async ({ page }) => {
  await page.goto("/skills");

  // 冷启动 backend 可能慢，给 manifest 抓取一个稍长的超时
  await expect(page.getByText("document_convert")).toBeVisible({ timeout: 15_000 });
  await expect(page.getByText("v1.0.0")).toBeVisible();
  await expect(page.getByText("medium").first()).toBeVisible();

  // 展开参数
  const details = page.locator("details").first();
  await details.click();
  await expect(page.getByText("source_path")).toBeVisible();
  await expect(page.getByText("target_format")).toBeVisible();

  // 允许工具行
  await expect(page.getByText(/exec\.shell/)).toBeVisible();
});
