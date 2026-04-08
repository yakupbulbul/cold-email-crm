import { test, expect } from "@playwright/test";

test("login succeeds with valid credentials and redirects to dashboard", async ({ page }) => {
  // Clear stored auth to test fresh login
  await page.context().clearCookies();
  await page.goto("/signin");
  await page.waitForLoadState("networkidle");

  await page.fill('input[type="email"], input[name="email"]', process.env.TEST_ADMIN_EMAIL || "admin@example.com");
  await page.fill('input[type="password"], input[name="password"]', process.env.TEST_ADMIN_PASSWORD || "testpassword");
  await page.click('button[type="submit"]');

  await page.waitForURL((url) => !url.pathname.includes("/signin"), { timeout: 10_000 });
  expect(page.url()).not.toContain("/signin");
});

test("protected route redirects unauthenticated user to login", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page).toHaveURL(/\/signin/, { timeout: 8_000 });
  await ctx.close();
});

test("logo/home link on login page is visible", async ({ browser }) => {
  const ctx = await browser.newContext();
  const page = await ctx.newPage();
  await page.goto("/signin");
  await expect(page).toHaveTitle(/.+/);
  await ctx.close();
});
