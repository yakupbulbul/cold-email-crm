import { Page } from "@playwright/test";

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
  await page.fill('[data-testid="email-input"], input[type="email"], input[name="email"]', email);
  await page.fill('[data-testid="password-input"], input[type="password"], input[name="password"]', password);
  await page.click('[data-testid="login-button"], button[type="submit"]');
  await page.waitForURL((url) => !url.pathname.includes("/signin"), { timeout: 10_000 });
}
