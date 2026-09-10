import { expect, test } from "@playwright/test";

test("session shell opens conversations with chat, trace and team views", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator(".session-item").first()).toBeVisible();
  await page.locator(".session-item").first().click();
  await expect(page).toHaveURL(/\/sessions\//);
  await expect(page.getByText("User", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: /个 Agent/ })).toBeVisible();
  await page.getByRole("button", { name: /个 Agent/ }).click();
  await expect(page.locator(".agent-row").first()).toBeVisible();
  await expect(page.getByText("实时提交依赖执行作业服务")).toBeVisible();

  await page.getByRole("link", { name: "轨迹" }).click();
  await expect(page.getByText("运行轨道")).toBeVisible();
  await page.getByRole("link", { name: "团队" }).click();
  await expect(page.getByRole("heading", { name: "协作流" })).toBeVisible();
  await page.getByRole("link", { name: "演进" }).click();
  await expect(page.getByText("演进证据在后台工作台")).toBeVisible();

  await page.getByRole("link", { name: "对话" }).click();
  await expect(page.getByText("在产物面板打开")).toBeVisible();
  await page.getByRole("button", { name: "在产物面板打开" }).click();
  await expect(page.getByText("产物 · 项目计划")).toBeVisible();
});

test("legacy evidence routes redirect into the dashboard", async ({ page }) => {
  await page.goto("/runs");
  await expect(page).toHaveURL(/\/dashboard\/runs/);
  await expect(page.getByRole("link", { name: "会话工作区" })).toBeVisible();
});
