import { expect, test } from "@playwright/test";

// Non-live: 进会话页确认右侧 Timeline 面板 + 顶栏 Activity toggle + 侧边铃铛
// 三个 v1.0 新 UI 在没有任何对话流的情况下也正确渲染。

test("conversation page: timeline panel + bell + toggle render", async ({ page, request }) => {
  // 起一个新会话
  const conv = await request.post("/api/proxy/conversations", {
    data: { title: "e2e timeline check" },
  });
  expect(conv.ok()).toBeTruthy();
  const convJson = await conv.json();

  await page.goto(`/c/${convJson.id}`);

  // 右侧 Timeline 面板存在，空态文案可见
  await expect(page.getByText(/Timeline/)).toBeVisible();
  await expect(page.getByText(/尚未开始执行/)).toBeVisible();

  // 顶栏 Activity toggle 可以收起/展开
  const toggle = page.locator('button[title^="收起 Timeline"], button[title^="展开 Timeline"]').first();
  await toggle.click();
  await expect(page.getByText(/尚未开始执行/)).not.toBeVisible();
  await toggle.click();
  await expect(page.getByText(/尚未开始执行/)).toBeVisible();

  // 侧边铃铛存在（badge 是否显示取决于通知数据，不强断言）
  await expect(page.locator('button[aria-label="通知"]')).toBeVisible();
});
