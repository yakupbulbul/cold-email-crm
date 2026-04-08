import { test, expect } from "@playwright/test";

test("mailboxes page loads", async ({ page }) => {
  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("create mailbox button is visible", async ({ page }) => {
  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");
  const btn = page.getByTestId("create-mailbox-button");
  await expect(btn).toBeVisible({ timeout: 6_000 });
});

test("mailboxes page shows honest provisioning mode guidance", async ({ page }) => {
  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");
  await expect(
    page.getByText(/Safe mode stores the mailbox locally only|Mutation mode creates the mailbox in Mailcow and CRM together/i),
  ).toBeVisible();
});

test("mailbox row actions render when mailboxes exist", async ({ page }) => {
  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");
  const editButtons = page.locator('[data-testid^="edit-mailbox-"]');
  const deleteButtons = page.locator('[data-testid^="delete-mailbox-"]');
  if ((await editButtons.count()) > 0) {
    await expect(editButtons.first()).toBeVisible();
    await expect(deleteButtons.first()).toBeVisible();
    await expect(page.getByText(/Mailcow synced|Local only/).first()).toBeVisible();
  } else {
    await expect(page.getByText("No Mailboxes Found")).toBeVisible();
  }
});
