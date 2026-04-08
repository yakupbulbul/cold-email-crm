import { test, expect } from "@playwright/test";

test("domains page loads and renders table or empty state", async ({ page }) => {
  await page.goto("/domains");
  await page.waitForLoadState("networkidle");
  const content = page.locator("table, [data-testid='empty-state'], h1, h2");
  await expect(content.first()).toBeVisible({ timeout: 8_000 });
});

test("create domain button is visible", async ({ page }) => {
  await page.goto("/domains");
  await page.waitForLoadState("networkidle");
  const btn = page.locator("button, a").filter({ hasText: /add|create|new domain/i }).first();
  await expect(btn).toBeVisible({ timeout: 6_000 });
});

test("domain can be removed from the domains page", async ({ page }) => {
  const suffix = Date.now().toString();
  const domainName = `delete-ui-${suffix}.example.com`;

  await page.goto("/domains");
  await page.fill('[data-testid="domain-name-input"]', domainName);
  await page.click('[data-testid="create-domain-button"]');
  await expect(page.getByText(domainName).last()).toBeVisible();

  const deleteButton = page.locator(`[data-testid^="delete-domain-"]`).filter({ hasText: /remove/i }).first();
  await deleteButton.click();

  await expect(page.getByText("Domain removed.")).toBeVisible();
  await expect(page.getByText(domainName).last()).toHaveCount(0);
});
