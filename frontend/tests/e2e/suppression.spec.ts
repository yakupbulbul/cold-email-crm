import { test, expect } from "@playwright/test";

test("suppression list page loads", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/suppression");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("suppression table or empty state renders", async ({ page }) => {
  await page.goto("/suppression");
  await page.waitForLoadState("networkidle");
  const el = page.locator("table, [data-testid='empty-state']").first();
  await expect(el).toBeVisible({ timeout: 8_000 });
});

test("add suppression button is visible", async ({ page }) => {
  await page.goto("/suppression");
  await page.waitForLoadState("networkidle");
  const btn = page.locator("button").filter({ hasText: /add|block|suppress/i }).first();
  await expect(btn).toBeVisible({ timeout: 6_000 });
});
