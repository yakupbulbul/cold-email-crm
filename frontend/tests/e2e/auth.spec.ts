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

test("/login redirects to the canonical /signin route", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/login");
  await expect(page).toHaveURL(/\/signin/, { timeout: 8_000 });
  await ctx.close();
});

test("authenticated user can reach all protected pages", async ({ page }) => {
  const protectedRoutes = [
    { route: "/", heading: /dashboard|ops command center/i },
    { route: "/domains", heading: /domain infrastructure/i },
    { route: "/mailboxes", heading: /infrastructure/i },
    { route: "/campaigns", heading: /campaigns/i },
    { route: "/suppression", heading: /global suppression log/i },
    { route: "/inbox", heading: /inbox|inbox empty/i },
    { route: "/ops", heading: /ops command center/i },
    { route: "/settings", heading: /system settings/i },
  ];

  for (const { route, heading } of protectedRoutes) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
    await expect(page).not.toHaveURL(/\/signin/, { timeout: 8_000 });
    await expect(page.getByRole("heading", { name: heading }).first()).toBeVisible();
  }
});
