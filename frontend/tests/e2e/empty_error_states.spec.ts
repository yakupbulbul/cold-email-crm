import { expect, test } from "@playwright/test";

test("no-seed empty states render as honest success states", async ({ page }) => {
  await page.route("**/api/v1/domains", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/campaigns", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/suppression", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/inbox/threads", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/settings/summary", async (route) => {
    await route.continue();
  });

  await page.goto("/domains");
  await expect(page.getByText("No Domains Added Yet")).toBeVisible();

  await page.goto("/mailboxes");
  await expect(page.getByText("No Mailboxes Found")).toBeVisible();

  await page.goto("/campaigns");
  await expect(page.getByText("No Campaigns Found")).toBeVisible();

  await page.goto("/suppression");
  await expect(page.getByText("No suppression entries yet.")).toBeVisible();

  await page.goto("/inbox");
  await expect(page.getByText("Inbox Empty")).toBeVisible();
});

test("settings and inbox show honest backend failure states", async ({ page }) => {
  await page.route("**/api/v1/settings/summary", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Settings service unavailable" }),
    });
  });

  await page.goto("/settings");
  await expect(page.getByText("Failed to load system settings")).toBeVisible();
  await expect(page.getByText("Settings service unavailable")).toBeVisible();

  await page.unroute("**/api/v1/settings/summary");
  await page.route("**/api/v1/inbox/threads", async (route) => {
    await route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Inbox backend offline" }),
    });
  });

  await page.goto("/inbox");
  await expect(page.getByText("Inbox Unavailable")).toBeVisible();
  await expect(page.getByText("Inbox backend offline")).toBeVisible();
});
