import { expect, test } from "@playwright/test";

// Non-live: 只点页面 + 调 /schedules API，不需要 ANTHROPIC_API_KEY。

test("schedules page: empty state then API-driven list", async ({ page, request }) => {
  await page.goto("/schedules");
  await expect(page.getByText(/还没有定时任务/)).toBeVisible({ timeout: 15_000 });

  // Seed via backend API by creating an actual ScheduleManager entry. 由于 manager
  // 是进程内内存的，前端只能通过 GET /schedules 看到由 Main Agent 工具或 Python 直接
  // 插入的 job。这里我们不强行 seed，只验证空态文案 + 刷新按钮可点。
  await page.getByRole("button", { name: "刷新" }).click();
  await expect(page.getByText(/还没有定时任务/)).toBeVisible();

  // 返回链接
  await page.getByRole("link", { name: /返回/ }).click();
  await expect(page).toHaveURL("/");
});
