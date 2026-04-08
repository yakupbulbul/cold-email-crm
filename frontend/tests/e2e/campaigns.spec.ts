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
        lists_summary: {
          lead_count: 0,
          reachable_count: 0,
          risky_count: 0,
          invalid_count: 0,
          suppressed_count: 0,
          status_counts: {},
          lists: [],
        },
      },
    ];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/lists", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "list-1",
          name: "Verified High Score",
          description: "Reusable list",
          type: "static",
          created_at: "2026-04-08T10:00:00Z",
          updated_at: "2026-04-08T10:00:00Z",
          lead_count: 5,
          reachable_count: 4,
          risky_count: 1,
          invalid_count: 0,
          suppressed_count: 0,
          status_counts: { valid: 4, risky: 1 },
        },
      ]),
    });
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
  await expect(card.getByRole("button", { name: "Attach list" })).toBeVisible();
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
        lists_summary: {
          lead_count: 3,
          reachable_count: 3,
          risky_count: 0,
          invalid_count: 0,
          suppressed_count: 0,
          status_counts: { valid: 3 },
          lists: [],
        },
      },
    ];
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) });
  });
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/lists", async (route) => {
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

test("campaign cards can be edited and saved", async ({ page }) => {
  const campaignId = "22222222-2222-2222-2222-222222222222";
  let campaign = {
    id: campaignId,
    name: "Editable Campaign",
    status: "draft",
    mailbox_id: "33333333-3333-3333-3333-333333333333",
    template_subject: "Old Subject",
    template_body: "Old Body",
    daily_limit: 25,
    created_at: "2026-04-08T10:00:00Z",
    lead_count: 0,
    sent_count: 0,
    reply_rate: "0%",
    lists_summary: {
      lead_count: 0,
      reachable_count: 0,
      risky_count: 0,
      invalid_count: 0,
      suppressed_count: 0,
      status_counts: {},
      lists: [],
    },
  };

  await page.route("**/api/v1/campaigns", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([campaign]) });
  });
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "33333333-3333-3333-3333-333333333333",
          email: "sender@example.com",
          display_name: "Sender",
          status: "active",
          daily_send_limit: 50,
          current_warmup_stage: 0,
          warmup_enabled: false,
          created_at: "2026-04-08T10:00:00Z",
        },
      ]),
    });
  });
  await page.route("**/api/v1/lists", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route(`**/api/v1/campaigns/${campaignId}`, async (route) => {
    const payload = JSON.parse(route.request().postData() || "{}");
    campaign = {
      ...campaign,
      name: payload.name,
      mailbox_id: payload.mailbox_id,
      template_subject: payload.template_subject,
      template_body: payload.template_body,
      daily_limit: payload.daily_limit,
    };
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(campaign) });
  });

  await page.goto("/campaigns");

  const card = page.getByTestId(`campaign-card-${campaignId}`);
  await card.getByRole("button", { name: "Edit" }).click();
  await page.getByTestId(`edit-campaign-name-${campaignId}`).fill("Updated Campaign");
  await page.getByTestId(`edit-campaign-subject-${campaignId}`).fill("New Subject");
  await page.getByTestId(`edit-campaign-body-${campaignId}`).fill("New Body");
  await page.getByTestId(`edit-campaign-limit-${campaignId}`).fill("40");
  await card.getByRole("button", { name: "Save" }).click();

  await expect(page.getByText("Campaign Updated Campaign updated.")).toBeVisible();
  await expect(card).toContainText("Updated Campaign");
  await expect(card).toContainText("40");
});

test("campaigns can attach reusable lists and show deduplicated summary", async ({ page }) => {
  const campaignId = "44444444-4444-4444-4444-444444444444";
  let attached = false;

  await page.route("**/api/v1/campaigns", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: campaignId,
          name: "List Driven Campaign",
          status: "draft",
          mailbox_id: "33333333-3333-3333-3333-333333333333",
          template_subject: "Subject",
          template_body: "Body",
          daily_limit: 25,
          created_at: "2026-04-08T10:00:00Z",
          lead_count: attached ? 2 : 0,
          sent_count: 0,
          reply_rate: "0%",
          lists_summary: {
            lead_count: attached ? 2 : 0,
            reachable_count: attached ? 1 : 0,
            risky_count: attached ? 1 : 0,
            invalid_count: 0,
            suppressed_count: 0,
            status_counts: attached ? { valid: 1, risky: 1 } : {},
            lists: attached ? [{
              id: "list-1",
              name: "April Outreach Batch",
              description: "Reusable list",
              type: "static",
              created_at: "2026-04-08T10:00:00Z",
              updated_at: "2026-04-08T10:00:00Z",
              lead_count: 2,
              reachable_count: 1,
              risky_count: 1,
              invalid_count: 0,
              suppressed_count: 0,
              status_counts: { valid: 1, risky: 1 },
            }] : [],
          },
        },
      ]),
    });
  });
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/lists", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "list-1",
          name: "April Outreach Batch",
          description: "Reusable list",
          type: "static",
          created_at: "2026-04-08T10:00:00Z",
          updated_at: "2026-04-08T10:00:00Z",
          lead_count: 2,
          reachable_count: 1,
          risky_count: 1,
          invalid_count: 0,
          suppressed_count: 0,
          status_counts: { valid: 1, risky: 1 },
        },
      ]),
    });
  });
  await page.route(`**/api/v1/campaigns/${campaignId}/lists`, async (route) => {
    attached = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        lead_count: 2,
        reachable_count: 1,
        risky_count: 1,
        invalid_count: 0,
        suppressed_count: 0,
        status_counts: { valid: 1, risky: 1 },
        lists: [],
      }),
    });
  });

  await page.goto("/campaigns");

  const card = page.getByTestId(`campaign-card-${campaignId}`);
  await card.getByRole("combobox").last().selectOption("list-1");
  await card.getByRole("button", { name: "Attach list" }).click();

  await expect(page.getByText("List attached to campaign.")).toBeVisible();
  await expect(card).toContainText("April Outreach Batch");
  await expect(card).toContainText("Deduped leads");
  await expect(card).toContainText("2");
});
