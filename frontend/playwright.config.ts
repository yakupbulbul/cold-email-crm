import { defineConfig, devices } from "@playwright/test";

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3000";

export default defineConfig({
  testDir: "./tests/e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: [
    ["html", { outputFolder: "../artifacts/playwright", open: "never" }],
    ["junit", { outputFile: "../artifacts/playwright/results.xml" }],
    ["list"],
  ],
  use: {
    baseURL: BASE_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "on-first-retry",
  },
  projects: [
    // Auth state setup (logs in once, reuses cookies)
    {
      name: "setup",
      testMatch: /.*\.setup\.ts/,
    },
    // Main desktop suite
    {
      name: "chromium",
      use: {
        ...devices["Desktop Chrome"],
        storageState: "tests/.auth/user.json",
      },
      dependencies: ["setup"],
    },
    // Mobile smoke pass
    {
      name: "mobile-smoke",
      testMatch: ["**/dashboard.spec.ts"],
      use: {
        ...devices["Pixel 5"],
        storageState: "tests/.auth/user.json",
      },
      dependencies: ["setup"],
    },
  ],
});
