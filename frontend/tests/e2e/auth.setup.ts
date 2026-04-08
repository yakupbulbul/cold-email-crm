import { test as setup } from "@playwright/test";
import path from "path";
import { loginAsBootstrapAdmin } from "../utils/auth";

const authFile = path.join(__dirname, "../.auth/user.json");

setup("authenticate as admin", async ({ page }) => {
  await loginAsBootstrapAdmin(page);
  await page.context().storageState({ path: authFile });
});
