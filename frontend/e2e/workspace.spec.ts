import { test, expect } from "@playwright/test";

/* Session Workspace (V3 Phase 1–3) acceptance over the scripted fixture.
   The replay takes ~22s end to end, so streaming tests get a longer budget.
   Fixture honesty: the workspace never calls the network (verified below). */

test.describe("workspace", () => {
  test("new session hero -> submit -> live replay -> fold complete", async ({
    page,
  }) => {
    test.setTimeout(75_000);
    const requests: string[] = [];
    page.on("request", (r) => requests.push(r.url()));

    await page.goto("/sessions/new");
    await expect(
      page.getByText("今天想完成什么？", { exact: true }),
    ).toBeVisible();
    await expect(page.locator(".ws-side-panel")).toHaveCount(0);

    await page.getByRole("button", { name: "项目计划", exact: true }).click();
    await expect(page.locator(".ws-user-bubble")).toBeVisible();
    await expect(page.locator(".ws-agent-block").first()).toBeVisible();
    // V3 §11.1: the first runtime event auto-opens the Live Execution Graph
    // at >=1280, and one event drives both Chat and the Graph.
    await expect(page).toHaveURL(/panel=execution/);
    await expect(page.locator(".ws-exec-node").first()).toBeVisible();

    await expect(page.locator(".ws-fold-head")).toBeVisible({
      timeout: 45_000,
    });
    await expect(page.locator(".ws-fold-stats")).toContainText("5 Agents");
    await expect(
      page.getByText("最终计划与风险清单已生成"),
    ).toBeVisible();
    // Finished: the Composer returns to the disabled send state.
    await expect(
      page.getByRole("button", { name: "发送任务" }),
    ).toBeDisabled();
    // Read-only guarantee: the scripted workspace touches no network route
    // beyond the dev-server's own module graph.
    expect(
      requests.filter((u) => !/5174|\/@|vite|node_modules/.test(u)),
    ).toEqual([]);
  });

  test("chat <-> graph locate shares one AgentRun and tool identity", async ({
    page,
  }) => {
    await page.goto(
      "/sessions/session-dependency-check?view=chat&panel=execution",
    );
    const verifierRun = "agent-run:fixture-run-live-1:verifier-1";
    await page.locator(`[data-flow-key="${verifierRun}"] .ws-agent-row`).click();
    // Chat row click must flash both identities at once (V3 §11.7).
    await expect(
      page.locator(`.ws-exec-node[data-flow-key="${verifierRun}"]`),
    ).toHaveClass(/ws-locate-flash/);

    // Tool-level identity: expand tools, click the Chat tool row, and its
    // graph Tool node must flash (callId wins over owner agentRunId).
    await page.locator('button[title="显示工具节点"]').click();
    const chatTool = page.locator(
      `[data-flow-key="${verifierRun}"] [data-flow-key="tool:call-check-1"]`,
    );
    await expect(chatTool).toBeVisible();
    await chatTool.click();
    await expect(
      page.locator('.ws-exec-node[data-flow-key="tool:call-check-1"]'),
    ).toHaveClass(/ws-locate-flash/);
  });

  test("V3 §27: below 1280 the panel stays closed and opens as overlay", async ({
    page,
  }) => {
    await page.setViewportSize({ width: 1100, height: 800 });
    await page.goto("/sessions/session-dependency-check");
    await expect(page.locator(".ws-side-panel")).toHaveCount(0);
    const chatWidth = await page
      .locator(".ws-view")
      .evaluate((el) => el.getBoundingClientRect().width);
    await page.getByRole("button", { name: "执行图", exact: true }).click();
    const panel = page.locator(".ws-side-panel");
    await expect(panel).toBeVisible();
    expect(await panel.evaluate((el) => getComputedStyle(el).position)).toBe(
      "fixed",
    );
    // Chat is not squeezed by the overlay (>= its pre-open width).
    const after = await page
      .locator(".ws-view")
      .evaluate((el) => el.getBoundingClientRect().width);
    expect(after).toBeGreaterThanOrEqual(chatWidth - 1);
  });

  test("sidebar navigation switches sessions and keeps views honest", async ({
    page,
  }) => {
    await page.goto("/sessions/session-publish-plan");
    await expect(page.locator(".ws-task-title")).toHaveText(
      "产品发布排期：识别共享工程师的资源冲突",
    );
    await page
      .locator(".ws-session-row")
      .filter({ hasText: "预算约束下的交付范围收窄分析" })
      .click();
    await expect(page).toHaveURL(/session-budget-review/);
    await expect(page.locator(".ws-task-title")).toHaveText(
      "预算约束下的交付范围收窄分析",
    );
    // Trace/Team/Evolution are placeholders this round, not fake data.
    await page.getByRole("button", { name: "演进", exact: true }).click();
    await expect(
      page.getByText("Strategy Diff / Trigger / Gate 在 V3 Phase 6 交付"),
    ).toBeVisible();
  });
});
