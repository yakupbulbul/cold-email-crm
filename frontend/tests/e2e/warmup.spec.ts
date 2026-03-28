import { test, expect } from "@playwright/test";

test("warmup page loads without crashing", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/warmup");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("warmup status cards or empty state visible", async ({ page }) => {
  await page.goto("/warmup");
  await page.waitForLoadState("networkidle");
  const el = page.locator("table, [data-testid='empty-state'], .card, article, section").first();
  await expect(el).toBeVisible({ timeout: 8_000 });
});
