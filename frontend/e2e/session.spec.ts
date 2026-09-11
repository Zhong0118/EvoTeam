import { expect, test } from "@playwright/test";

test("session workspace renders chat, trace, team and evolution views", async ({
  page,
}) => {
  test.setTimeout(60000);
  await page.goto("/");
  await expect(page.locator(".ws-session-item").first()).toBeVisible();
  await page.locator(".ws-session-item").first().click();
  await expect(page.getByText("你", { exact: true })).toBeVisible();
  await expect(page.locator(".ws-process-block")).toBeVisible();
  // 过程折叠
  await page.locator(".ws-process-summary-row").first().click();
  await expect(page.locator(".ws-process-row").first()).toBeVisible();
  // 产物芯片打开右侧面板
  await page.getByText("项目计划", { exact: true }).click();
  await expect(page.getByText("ARTIFACT · PLAN")).toBeVisible();
  await page.getByRole("button", { name: "关闭面板" }).click();

  // 轨迹：时间线 + 表格 + 检查器
  await page.getByRole("button", { name: "轨迹" }).click();
  await expect(page.locator(".ws-timeline-overview")).toBeVisible();
  await page.locator(".ws-trace-table tbody tr").first().click();
  await expect(page.getByText("TRACE EVENT")).toBeVisible();
  await page.getByRole("button", { name: "关闭面板" }).click();

  // 团队：图谱节点 + 检查器
  await page.getByRole("button", { name: "团队" }).click();
  await expect(page.locator(".ws-agent-node").first()).toBeVisible();
  await page.locator(".ws-agent-node").first().click();
  await expect(page.getByText("TEAM · AGENT")).toBeVisible();
  await page.getByRole("button", { name: "只看该 Agent 轨迹" }).click();
  await expect(page.getByText("TRACE EVENT")).toHaveCount(0);

  // 演进：fixture 数据有记录时展示故事线，否则展示诚实空态
  await page.getByRole("button", { name: "演进" }).click();
  const hasEvolution = (await page.locator(".ws-evo-graphs").count()) > 0;
  if (hasEvolution) {
    await expect(page.getByText("为什么触发演进？")).toBeVisible();
    await expect(page.getByText("CHANGED")).toBeVisible();
  } else {
    await expect(page.getByText(/还没有演进记录/)).toBeVisible();
  }

  // 回到对话：Composer 不冒充可用
  await page.getByRole("button", { name: "对话" }).click();
  await page.getByRole("button", { name: "发送" }).click();
  await expect(page.getByText(/实时提交依赖执行作业服务/)).toBeVisible();
});

test("legacy evidence routes redirect into the dashboard", async ({ page }) => {
  await page.goto("/runs");
  await expect(page).toHaveURL(/\/dashboard\/runs/);
  await expect(page.getByRole("link", { name: "会话工作区" })).toBeVisible();
});
