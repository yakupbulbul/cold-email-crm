import { test, expect } from "@playwright/test";

test("public landing page loads without JS errors", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: /run cold email infrastructure/i })).toBeVisible({ timeout: 8_000 });
  await expect(page.getByRole("link", { name: /sign in to workspace|open workspace/i }).first()).toBeVisible();
});

test("dashboard route renders inside the authenticated shell", async ({ page }) => {
  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");
  await expect(page.locator('a[href="/dashboard"]').first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /dashboard overview/i })).toBeVisible();
});

test("sidebar navigation links are present on the dashboard shell", async ({ page }) => {
  await page.goto("/dashboard");
  await page.waitForLoadState("networkidle");
  for (const href of ["/domains", "/mailboxes", "/campaigns", "/contacts", "/ops"]) {
    await expect(page.locator(`a[href="${href}"]`).first()).toBeVisible();
  }
});

test("mobile viewport — public landing page renders cleanly", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: /run cold email infrastructure/i })).toBeVisible({ timeout: 8_000 });
  await expect(page.getByRole("link", { name: /sign in|open workspace/i }).first()).toBeVisible();
});
