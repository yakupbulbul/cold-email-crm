import { test, expect } from "@playwright/test";

test("campaigns list page loads", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/campaigns");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("create campaign button is visible", async ({ page }) => {
  await page.goto("/campaigns");
  await page.waitForLoadState("networkidle");
  const btn = page.locator("button, a").filter({ hasText: /create|new campaign/i }).first();
  await expect(btn).toBeVisible({ timeout: 6_000 });
});

test("campaign table or empty state renders", async ({ page }) => {
  await page.goto("/campaigns");
  await page.waitForLoadState("networkidle");
  const el = page.locator("table, [data-testid='empty-state'], ul").first();
  await expect(el).toBeVisible({ timeout: 8_000 });
});
