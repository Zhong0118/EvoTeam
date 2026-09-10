import { test, expect } from "@playwright/test";
test("real SQLite evidence loads through read-only HTTP and survives refresh", async ({
  page,
}) => {
  const writes: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/v1/") && r.method() !== "GET") writes.push(r.url());
  });
  await page.goto("/runs");
  await expect(page.getByText("当前数据库", { exact: true })).toBeVisible();
  await page
    .getByRole("link", { name: /^查看 / })
    .first()
    .click();
  await expect(page.getByText("校验通过", { exact: true })).toBeVisible();
  await page.getByRole("link", { name: "查看 Trace", exact: true }).click();
  await expect(page.locator(".event-row").first()).toBeVisible();
  await page.reload();
  await expect(page.locator(".event-row").first()).toBeVisible();
  expect(writes).toEqual([]);
});
test("offline does not silently switch to fixture", async ({ page }) => {
  await page.route("**/v1/**", (route) => route.abort());
  await page.goto("/runs");
  await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByText("开发样例 · 非实测")).toHaveCount(0);
});
