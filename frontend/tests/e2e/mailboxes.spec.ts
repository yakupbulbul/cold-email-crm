import { test, expect } from "@playwright/test";

test("mailboxes page loads", async ({ page }) => {
  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("create mailbox button is visible", async ({ page }) => {
  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");
  const btn = page.locator("button, a").filter({ hasText: /add|create|new mailbox/i }).first();
  await expect(btn).toBeVisible({ timeout: 6_000 });
});
