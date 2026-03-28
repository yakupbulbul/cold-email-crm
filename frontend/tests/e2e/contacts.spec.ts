import { test, expect } from "@playwright/test";

test("contacts page loads", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/contacts");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("contacts table or empty state renders", async ({ page }) => {
  await page.goto("/contacts");
  await page.waitForLoadState("networkidle");
  const el = page.locator("table, [data-testid='empty-state']").first();
  await expect(el).toBeVisible({ timeout: 8_000 });
});

test("CSV import page loads", async ({ page }) => {
  await page.goto("/contacts/import");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2, [data-testid='csv-dropzone'], input[type='file']").first()).toBeVisible({ timeout: 8_000 });
});
