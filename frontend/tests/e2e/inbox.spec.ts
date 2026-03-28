import { test, expect } from "@playwright/test";

test("inbox page loads without crashing", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/inbox");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("inbox shows thread list or empty state", async ({ page }) => {
  await page.goto("/inbox");
  await page.waitForLoadState("networkidle");
  const el = page.locator("[data-testid='thread-list'], table, [data-testid='empty-state'], ul, ol").first();
  await expect(el).toBeVisible({ timeout: 8_000 });
});
