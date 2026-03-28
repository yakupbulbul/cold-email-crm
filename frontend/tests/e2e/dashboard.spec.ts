import { test, expect } from "@playwright/test";

test("dashboard loads without JS errors", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  // At least one heading or stat card is visible
  const heading = page.locator("h1, h2").first();
  await expect(heading).toBeVisible({ timeout: 8_000 });
});

test("sidebar navigation links are present", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  for (const href of ["/domains", "/mailboxes", "/campaigns", "/contacts"]) {
    const link = page.locator(`a[href="${href}"]`);
    await expect(link).toBeVisible();
  }
});

test("ops sidebar section is present", async ({ page }) => {
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  await expect(page.locator('a[href="/ops"]')).toBeVisible();
  await expect(page.locator('a[href="/ops/alerts"]')).toBeVisible();
});

test("mobile viewport — dashboard renders and nav is accessible", async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await page.goto("/");
  await page.waitForLoadState("networkidle");
  const heading = page.locator("h1, h2").first();
  await expect(heading).toBeVisible({ timeout: 8_000 });
});
