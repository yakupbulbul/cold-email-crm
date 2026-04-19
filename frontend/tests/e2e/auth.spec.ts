import { test, expect } from "@playwright/test";
import { loginAsBootstrapAdmin } from "../utils/auth";

test("login succeeds with valid credentials and redirects to dashboard", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await loginAsBootstrapAdmin(page);

  await page.waitForURL((url) => !url.pathname.includes("/signin"), { timeout: 10_000 });
  expect(page.url()).not.toContain("/signin");
  await ctx.close();
});

test("protected dashboard route redirects unauthenticated user to login", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/signin/, { timeout: 8_000 });
  await ctx.close();
});

test("public landing page is accessible without authentication", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/");
  await expect(page).toHaveURL(/\/$/, { timeout: 8_000 });
  await expect(page.getByRole("heading", { name: /run cold email infrastructure/i })).toBeVisible();
  await ctx.close();
});

test("logo/home link on login page is visible", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/");
  await page.evaluate(() => window.localStorage.clear());
  await page.goto("/signin");
  await expect(page.getByRole("link", { name: /campaign manager/i }).first()).toBeVisible();
  await expect(page.getByRole("heading", { name: /access your workspace/i })).toBeVisible();
  await ctx.close();
});

test("password visibility toggle works on signin", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/signin");
  await expect(page.getByTestId("password-input")).toHaveAttribute("type", "password");
  await page.getByTestId("password-toggle").click();
  await expect(page.getByTestId("password-input")).toHaveAttribute("type", "text");
  await page.getByTestId("password-toggle").click();
  await expect(page.getByTestId("password-input")).toHaveAttribute("type", "password");
  await ctx.close();
});

test("/login redirects to the canonical /signin route", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/login");
  await expect(page).toHaveURL(/\/signin/, { timeout: 8_000 });
  await ctx.close();
});

test("authenticated user can reach all protected pages", async ({ page }) => {
  const protectedRoutes = ["/domains", "/ops", "/settings"];

  for (const route of protectedRoutes) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await expect(page).not.toHaveURL(/\/signin/, { timeout: 8_000 });
    await expect(page.getByText("Hydrating Secure Session...")).toHaveCount(0, { timeout: 10_000 });
    await expect(page.locator('a[href="/dashboard"]').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.locator("main")).toBeVisible({ timeout: 10_000 });
  }
});
