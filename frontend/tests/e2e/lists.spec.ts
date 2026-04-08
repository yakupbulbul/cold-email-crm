import { expect, test } from "@playwright/test";

test("lists page renders real list management sections", async ({ page }) => {
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
  await page.route("**/api/v1/leads", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "lead-1",
          email: "one@example.com",
          first_name: "One",
          last_name: "Lead",
          company: "Example",
          email_status: "valid",
          verification_score: 100,
          verification_integrity: "high",
          last_verified_at: "2026-04-08T10:00:00Z",
          is_disposable: false,
          is_role_based: false,
          is_suppressed: false,
          verification_reasons: ["Mailbox looks reachable."],
          list_ids: [],
          list_names: [],
          created_at: "2026-04-08T10:00:00Z",
        },
      ]),
    });
  });
  await page.route("**/api/v1/lists/list-1/leads", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        list: {
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
        leads: [],
      }),
    });
  });

  await page.goto("/lists");

  await expect(page.getByRole("heading", { name: "Lead Lists" })).toBeVisible();
  await expect(page.getByText("April Outreach Batch")).toBeVisible();
  await page.getByRole("button", { name: /April Outreach Batch/ }).click();
  await expect(page.getByText("Add lead to list")).toBeVisible();
  await expect(page.getByText("This list has no leads yet.")).toBeVisible();
});

test("edit button opens the selected list in edit mode", async ({ page }) => {
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
  await page.route("**/api/v1/leads", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/lists/list-1/leads", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        list: {
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
        leads: [],
      }),
    });
  });

  await page.goto("/lists");
  await page.locator('table button').nth(1).click();

  await expect(page.locator('input[value="April Outreach Batch"]')).toBeVisible();
  await expect(page.locator('input[value="Reusable list"]')).toBeVisible();
  await expect(page.getByRole("button", { name: "Save" })).toBeVisible();
});

test("list members can update contact type", async ({ page }) => {
  let listLead = {
    id: "lead-1",
    email: "one@example.com",
    first_name: "One",
    last_name: "Lead",
    company: "Example",
    contact_type: "b2c",
    consent_status: "granted",
    unsubscribe_status: "subscribed",
    contact_quality_tier: "medium",
    email_status: "valid",
    verification_score: 100,
    verification_integrity: "high",
    last_verified_at: "2026-04-08T10:00:00Z",
    is_disposable: false,
    is_role_based: false,
    is_suppressed: false,
    verification_reasons: ["Mailbox looks reachable."],
    list_ids: ["list-1"],
    list_names: ["April Outreach Batch"],
    created_at: "2026-04-08T10:00:00Z",
  };

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
          lead_count: 1,
          reachable_count: 1,
          risky_count: 0,
          invalid_count: 0,
          suppressed_count: 0,
          contact_type_counts: { b2c: 1 },
          status_counts: { valid: 1 },
        },
      ]),
    });
  });
  await page.route("**/api/v1/leads", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([listLead]) });
  });
  await page.route("**/api/v1/lists/list-1/leads", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        list: {
          id: "list-1",
          name: "April Outreach Batch",
          description: "Reusable list",
          type: "static",
          created_at: "2026-04-08T10:00:00Z",
          updated_at: "2026-04-08T10:00:00Z",
          lead_count: 1,
          reachable_count: 1,
          risky_count: 0,
          invalid_count: 0,
          suppressed_count: 0,
          contact_type_counts: { b2c: 1 },
          status_counts: { valid: 1 },
        },
        leads: [listLead],
      }),
    });
  });
  await page.route("**/api/v1/leads/lead-1", async (route) => {
    listLead = { ...listLead, ...JSON.parse(route.request().postData() || "{}") };
    if (listLead.contact_type === "mixed") listLead.contact_type = null;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(listLead) });
  });

  await page.goto("/lists");
  await page.getByText("April Outreach Batch").click();
  await page.locator("select").filter({ has: page.getByRole("option", { name: "B2B" }) }).last().selectOption("b2b");
  await page.getByRole("button", { name: "Save" }).last().click();

  await expect(page.getByText("Updated one@example.com contact type to b2b.")).toBeVisible();
});

test("selected list members can update contact type in bulk", async ({ page }) => {
  let listLeads = [
    {
      id: "lead-1",
      email: "one@example.com",
      first_name: "One",
      last_name: "Lead",
      company: "Example",
      contact_type: "b2c",
      consent_status: "granted",
      unsubscribe_status: "subscribed",
      contact_quality_tier: "medium",
      email_status: "valid",
      verification_score: 100,
      verification_integrity: "high",
      last_verified_at: "2026-04-08T10:00:00Z",
      is_disposable: false,
      is_role_based: false,
      is_suppressed: false,
      verification_reasons: ["Mailbox looks reachable."],
      list_ids: ["list-1"],
      list_names: ["April Outreach Batch"],
      created_at: "2026-04-08T10:00:00Z",
    },
    {
      id: "lead-2",
      email: "two@example.com",
      first_name: "Two",
      last_name: "Lead",
      company: "Example",
      contact_type: null,
      consent_status: "unknown",
      unsubscribe_status: "subscribed",
      contact_quality_tier: "low",
      email_status: "unverified",
      verification_score: null,
      verification_integrity: null,
      last_verified_at: null,
      is_disposable: false,
      is_role_based: false,
      is_suppressed: false,
      verification_reasons: null,
      list_ids: ["list-1"],
      list_names: ["April Outreach Batch"],
      created_at: "2026-04-08T10:00:00Z",
    },
  ];

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
          risky_count: 0,
          invalid_count: 1,
          suppressed_count: 0,
          contact_type_counts: { b2c: 1, mixed: 1 },
          status_counts: { valid: 1, unverified: 1 },
        },
      ]),
    });
  });
  await page.route("**/api/v1/leads", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(listLeads) });
  });
  await page.route("**/api/v1/lists/list-1/leads", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        list: {
          id: "list-1",
          name: "April Outreach Batch",
          description: "Reusable list",
          type: "static",
          created_at: "2026-04-08T10:00:00Z",
          updated_at: "2026-04-08T10:00:00Z",
          lead_count: 2,
          reachable_count: 1,
          risky_count: 0,
          invalid_count: 1,
          suppressed_count: 0,
          contact_type_counts: { b2c: 1, mixed: 1 },
          status_counts: { valid: 1, unverified: 1 },
        },
        leads: listLeads,
      }),
    });
  });
  await page.route("**/api/v1/leads/bulk/contact-type", async (route) => {
    const payload = JSON.parse(route.request().postData() || "{}");
    listLeads = listLeads.map((lead) =>
      payload.lead_ids.includes(lead.id)
        ? { ...lead, contact_type: payload.contact_type === "mixed" ? null : payload.contact_type }
        : lead,
    );
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ status: "updated", lead_count: payload.lead_ids.length, contact_type: payload.contact_type === "mixed" ? null : payload.contact_type }),
    });
  });

  await page.goto("/lists");
  await page.getByText("April Outreach Batch").click();
  await page.getByLabel("Select one@example.com").check();
  await page.getByLabel("Select two@example.com").check();
  await page.getByLabel("Bulk member contact type").selectOption("b2b");
  await page.getByRole("button", { name: "Apply" }).click();

  await expect(page.getByText("Updated 2 leads to b2b.")).toBeVisible();
});
