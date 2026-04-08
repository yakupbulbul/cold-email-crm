import { test as setup } from "@playwright/test";
import fs from "fs";
import path from "path";

const authFile = path.join(__dirname, "../.auth/user.json");
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

setup("authenticate as admin", async ({ page }) => {
  const email =
    process.env.TEST_ADMIN_EMAIL ||
    getBootstrapEnvValue("BOOTSTRAP_ADMIN_EMAIL") ||
    "admin@example.com";
  const password =
    process.env.TEST_ADMIN_PASSWORD ||
    getBootstrapEnvValue("BOOTSTRAP_ADMIN_PASSWORD") ||
    "replace-with-a-local-admin-password";

  await page.goto("/signin");
  await page.fill('[data-testid="email-input"], input[type="email"], input[name="email"]', email);
  await page.fill('[data-testid="password-input"], input[type="password"], input[name="password"]', password);
  await page.click('[data-testid="login-button"], button[type="submit"]');

  // Wait for redirect away from the auth route.
  await page.waitForURL((url) => !url.pathname.includes("/signin"), { timeout: 10_000 });
  await page.context().storageState({ path: authFile });
});
