import { test, expect } from "@playwright/test";
test("all evidence routes, filters, duplicate instances, replay and source labels", async ({
  page,
}) => {
  const writes: string[] = [];
  page.on("request", (r) => {
    if (!["GET", "HEAD"].includes(r.method())) writes.push(r.url());
  });
  await page.goto("/runs");
  await expect(page.getByText("开发样例 · 非实测")).toBeVisible();
  await expect(
    page.getByRole("link", { name: "查看 fixture-run-1", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "隔离验证", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "查看 fixture-run-3", exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "查看 fixture-run-1", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "全部用途", exact: true }).click();
  await page
    .getByRole("link", { name: "查看 fixture-run-2", exact: true })
    .click();
  await expect(page.getByText("校验未通过", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "查看 Trace", exact: true }).click();
  await expect(page.getByText("配置节点 3 · 执行实例 5")).toBeVisible();
  await page.getByRole("button", { name: "下一步", exact: true }).click();
  await expect(page).toHaveURL(/event=/);
  await page.locator(".event-row").nth(2).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("combobox")).toContainText(
    "fixture-1-executor-1",
  );
  await page.getByRole("combobox").selectOption("fixture-1-executor-3");
  await expect(page).toHaveURL(/instance=fixture-1-executor-3/);
  await page.keyboard.press("Escape");
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(page.locator(".event-row").nth(2)).toBeFocused();
  await page.getByRole("link", { name: "演进证据", exact: true }).click();
  await page
    .getByRole("link", { name: "查看证据链", exact: true })
    .first()
    .click();
  await page.getByRole("button", { name: "独立验证" }).click();
  await expect(page.getByText("独立样本不足，随机种子未应用")).toBeVisible();
  await page.getByRole("link", { name: "查看策略版本" }).click();
  await expect(
    page.getByRole("heading", { name: "正式版本", exact: true }),
  ).toBeVisible();
  expect(writes).toEqual([]);
});
test("narrow screen, missing data and 404 remain readable", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.emulateMedia({ reducedMotion: "reduce" });
  await page.goto("/runs/fixture-run-4");
  await expect(page.getByText("该记录未提供完整任务快照")).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "打开导航" }).click();
  await expect(
    page.getByRole("link", { name: "演进证据", exact: true }),
  ).toBeVisible();
  await page.goto("/runs/no-such");
  await expect(page.getByRole("alert")).toContainText("404");
});

test("capture desktop and mobile evidence views", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 });
  for (const [name, path] of [
    ["runs", "/runs"],
    ["detail", "/runs/fixture-run-1"],
    ["trace", "/runs/fixture-run-2/trace"],
    ["evolution", "/evolutions/fixture-evolution-1?stage=validation"],
    ["versions", "/strategies/demo-project-planning"],
  ]) {
    await page.goto(path);
    await expect(page.locator(".source-note")).toBeVisible();
    await page.screenshot({
      path: `screenshots/${name}-desktop.png`,
      fullPage: true,
    });
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/runs/fixture-run-2/trace");
  await expect(page.locator(".event-row").first()).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.screenshot({
    path: "screenshots/trace-mobile.png",
    fullPage: true,
  });
});
