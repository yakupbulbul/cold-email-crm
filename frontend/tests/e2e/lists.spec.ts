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
