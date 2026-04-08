import { expect, test } from "@playwright/test";

test("campaign cards expose activation controls and show honest lean-mode start blocking", async ({ page }) => {
  const campaignId = "00000000-0000-0000-0000-000000000001";

  await page.route("**/api/v1/campaigns", async (route) => {
    const payload = [
      {
        id: campaignId,
        name: "Mock Draft Campaign",
        status: "draft",
        template_subject: "Subject",
        template_body: "Body",
        daily_limit: 25,
        created_at: "2026-04-08T10:00:00Z",
        lead_count: 0,
        sent_count: 0,
        reply_rate: "0%",
      },
    ];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route(`**/api/v1/campaigns/${campaignId}/start`, async (route) => {
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        detail: "Background workers are disabled in low-RAM mode. Run make dev or make dev-full before starting campaigns.",
      }),
    });
  });

  await page.goto("/campaigns");

  const card = page.getByTestId(`campaign-card-${campaignId}`);
  await expect(card).toBeVisible();
  await expect(card.getByRole("button", { name: "Start" })).toBeVisible();
  await expect(card.getByRole("button", { name: "Preflight" })).toBeVisible();
  await card.getByRole("button", { name: "Start" }).click();
  await expect(card.locator('[data-testid^="campaign-message-"]')).toContainText("make dev or make dev-full");
});

test("active campaigns show pause and update status after pause succeeds", async ({ page }) => {
  const campaignId = "11111111-1111-1111-1111-111111111111";
  let paused = false;

  await page.route("**/api/v1/campaigns", async (route) => {
    const payload = [
      {
        id: campaignId,
        name: "Mock Active Campaign",
        status: paused ? "paused" : "active",
        template_subject: "Subject",
        template_body: "Body",
        daily_limit: 25,
        created_at: "2026-04-08T10:00:00Z",
        lead_count: 3,
        sent_count: 1,
        reply_rate: "0%",
      },
    ];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route(`**/api/v1/campaigns/${campaignId}/pause`, async (route) => {
    paused = true;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ status: "paused" }) });
  });

  await page.goto("/campaigns");

  const card = page.getByTestId(`campaign-card-${campaignId}`);
  await expect(card).toBeVisible();
  await expect(card.getByRole("button", { name: "Pause" })).toBeVisible();

  await card.getByRole("button", { name: "Pause" }).click();

  await expect(page.getByText("Campaign paused.")).toBeVisible();
  await expect(page.getByTestId(`campaign-status-${campaignId}`)).toContainText("paused");
});
