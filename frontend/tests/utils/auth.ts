import { expect, Page } from "@playwright/test";

import { getRepoEnvValue } from "./env";

export function bootstrapAdminCredentials() {
  return {
    email:
      process.env.TEST_ADMIN_EMAIL ||
      getRepoEnvValue("BOOTSTRAP_ADMIN_EMAIL") ||
      "admin@example.com",
    password:
      process.env.TEST_ADMIN_PASSWORD ||
      getRepoEnvValue("BOOTSTRAP_ADMIN_PASSWORD") ||
      "replace-with-a-local-admin-password",
  };
}

export async function loginAsBootstrapAdmin(page: Page) {
  const { email, password } = bootstrapAdminCredentials();
  await page.goto("/signin");
  await page.getByTestId("email-input").fill(email);
  await page.getByTestId("password-input").fill(password);
  await expect(page.getByTestId("login-button")).toBeEnabled({ timeout: 10_000 });
  await page.getByTestId("login-button").click();
  await page.waitForFunction(() => window.localStorage.getItem("token"), undefined, { timeout: 10_000 });
  if (new URL(page.url()).pathname.includes("/signin")) {
    await page.goto("/dashboard");
  }
  await page.waitForURL((url) => url.pathname === "/dashboard" || !url.pathname.includes("/signin"), { timeout: 10_000 });
}
