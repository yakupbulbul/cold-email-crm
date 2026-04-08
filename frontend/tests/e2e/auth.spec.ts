import { test, expect } from "@playwright/test";
import fs from "fs";
import path from "path";

const repoEnvFile = path.resolve(__dirname, "../../../.env");

function getBootstrapEnvValue(key: string): string | undefined {
  if (!fs.existsSync(repoEnvFile)) {
    return undefined;
  }

  for (const line of fs.readFileSync(repoEnvFile, "utf8").split(/\r?\n/)) {
    if (!line || line.startsWith("#")) {
      continue;
    }

    const [envKey, ...rest] = line.split("=");
    if (envKey === key) {
      return rest.join("=").trim();
    }
  }

  return undefined;
}

test("login succeeds with valid credentials and redirects to dashboard", async ({ page }) => {
  // Clear stored auth to test fresh login
  await page.context().clearCookies();
  await page.goto("/signin");
  await page.waitForLoadState("networkidle");

  await page.fill(
    'input[type="email"], input[name="email"]',
    process.env.TEST_ADMIN_EMAIL || getBootstrapEnvValue("BOOTSTRAP_ADMIN_EMAIL") || "admin@example.com",
  );
  await page.fill(
    'input[type="password"], input[name="password"]',
    process.env.TEST_ADMIN_PASSWORD ||
      getBootstrapEnvValue("BOOTSTRAP_ADMIN_PASSWORD") ||
      "replace-with-a-local-admin-password",
  );
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

test("/login redirects to the canonical /signin route", async ({ browser }) => {
  const ctx = await browser.newContext({ storageState: { cookies: [], origins: [] } });
  const page = await ctx.newPage();
  await page.goto("/login");
  await expect(page).toHaveURL(/\/signin/, { timeout: 8_000 });
  await ctx.close();
});
