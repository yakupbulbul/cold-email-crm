import { test as setup } from "@playwright/test";
import path from "path";

const authFile = path.join(__dirname, "../.auth/user.json");

setup("authenticate as admin", async ({ page }) => {
  const email = process.env.TEST_ADMIN_EMAIL || "admin@example.com";
  const password = process.env.TEST_ADMIN_PASSWORD || "testpassword";

  await page.goto("/signin");
  await page.fill('[data-testid="email-input"], input[type="email"], input[name="email"]', email);
  await page.fill('[data-testid="password-input"], input[type="password"], input[name="password"]', password);
  await page.click('[data-testid="login-button"], button[type="submit"]');

  // Wait for redirect away from the auth route.
  await page.waitForURL((url) => !url.pathname.includes("/signin"), { timeout: 10_000 });
  await page.context().storageState({ path: authFile });
});
