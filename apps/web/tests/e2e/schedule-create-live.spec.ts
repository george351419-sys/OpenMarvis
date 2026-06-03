import { expect, test } from "@playwright/test";

test.skip(!process.env.OPENMARVIS_E2E_LIVE, "需要 ANTHROPIC_API_KEY + OPENMARVIS_E2E_LIVE=1");

test("scheduler: create once-trigger via chat then see it in /schedules", async ({ page }) => {
  await page.goto("/");
  await page.waitForURL(/\/c\//);

  const textarea = page.locator("textarea");
  await textarea.fill(
    "用 create_schedule 创建一个 once 触发器：30 天后 (ISO datetime, UTC) 跑指令 'ping me'，描述 '冒烟'",
  );
  await page.keyboard.press("Meta+Enter");

  // confirm 卡片出现 → 点确认（create_schedule 是 medium-risk）
  const confirmBtn = page.getByRole("button", { name: /确认|批准|允许/ });
  await confirmBtn.waitFor({ timeout: 60_000 });
  await confirmBtn.click();

  // 等回复里出现 sch_ ID
  await expect(page.getByText(/sch_[a-f0-9]{12}/)).toBeVisible({ timeout: 60_000 });

  // 翻到 /schedules 应该能看到
  await page.goto("/schedules");
  await expect(page.getByText(/once/)).toBeVisible();
  await expect(page.getByText(/冒烟/)).toBeVisible();
});
