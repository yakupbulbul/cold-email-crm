import { test, expect } from "@playwright/test";

test("domains page loads and renders table or empty state", async ({ page }) => {
  await page.goto("/domains");
  await page.waitForLoadState("networkidle");
  const content = page.locator("table, [data-testid='empty-state'], h1, h2");
  await expect(content.first()).toBeVisible({ timeout: 8_000 });
});

test("create domain button is visible", async ({ page }) => {
  await page.goto("/domains");
  await page.waitForLoadState("networkidle");
  const btn = page.locator("button, a").filter({ hasText: /add|create|new domain/i }).first();
  await expect(btn).toBeVisible({ timeout: 6_000 });
});
