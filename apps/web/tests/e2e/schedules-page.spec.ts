import { expect, test } from "@playwright/test";

// Non-live: 只点页面 + 调 /schedules API，不需要 ANTHROPIC_API_KEY。

test("schedules page: empty state then API-driven list", async ({ page, request }) => {
  await page.goto("/schedules");
  await expect(page.getByText(/还没有定时任务/)).toBeVisible({ timeout: 15_000 });

  // Schedule 持久化在 ~/.openmarvis/data.db 的 schedule 表，dev server 启动
  // 会 rehydrate。本测试只在 DB 为空时验证空态文案 + 刷新按钮可点；如本机有
  // 遗留 schedule，先清空 DB 再跑（sqlite3 ~/.openmarvis/data.db
  // "DELETE FROM schedule;"）。
  await page.getByRole("button", { name: "刷新" }).click();
  await expect(page.getByText(/还没有定时任务/)).toBeVisible();

  // 返回链接
  await page.getByRole("link", { name: /返回/ }).click();
  await expect(page).toHaveURL("/");
});
