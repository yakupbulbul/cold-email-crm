import { expect, test } from "@playwright/test";

test.describe("contacts verification UI", () => {
  test("contacts page loads with verification controls", async ({ page }) => {
    await page.goto("/contacts");
    await expect(page.getByRole("heading", { name: "Lead Directory" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Verify selected" })).toBeVisible();
    await expect(page.locator("table")).toBeVisible();
  });

  test("unverified wording only appears as a status", async ({ page }) => {
    await page.goto("/contacts");
    await expect(page.getByText("Unverified means the email has not been checked yet.")).toBeVisible();
    await expect(page.getByText("unverified", { exact: false }).first()).toBeVisible();
  });

  test("contacts detail area opens", async ({ page }) => {
    await page.route("**/api/v1/leads", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "lead-1",
            email: "person@example.com",
            first_name: "Test",
            last_name: "Lead",
            company: "Orbitworks",
            email_status: "unverified",
            verification_score: null,
            verification_integrity: null,
            last_verified_at: null,
            is_disposable: false,
            is_role_based: false,
            is_suppressed: false,
            verification_reasons: null,
            list_ids: [],
            list_names: [],
            created_at: "2026-04-08T10:00:00Z",
          },
        ]),
      });
    });
    await page.route("**/api/v1/lists", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.goto("/contacts");
    const detailsButton = page.getByRole("button", { name: "Details" }).first();
    await expect(detailsButton).toBeVisible();
    await detailsButton.click();
    await expect(page.getByText("Latest verification state for this lead.")).toBeVisible();
  });

  test("verify actions surface real backend progress", async ({ page }) => {
    await page.route("**/api/v1/leads", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "lead-1",
            email: "person@example.com",
            first_name: "Test",
            last_name: "Lead",
            company: "Orbitworks",
            email_status: "unverified",
            verification_score: null,
            verification_integrity: null,
            last_verified_at: null,
            is_disposable: false,
            is_role_based: false,
            is_suppressed: false,
            verification_reasons: null,
            list_ids: [],
            list_names: [],
            created_at: "2026-04-08T10:00:00Z",
          },
        ]),
      });
    });
    await page.route("**/api/v1/lists", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.route("**/api/v1/leads/verify", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          lead_id: "lead-1",
          email: "person@example.com",
          status: "valid",
          score: 100,
          integrity: "high",
          reasons: ["Mailbox looks reachable."],
          checked_at: "2026-04-08T10:00:00Z",
          syntax_valid: true,
          domain_valid: true,
          mx_valid: true,
          is_disposable: false,
          is_role_based: false,
          is_duplicate: false,
          is_suppressed: false,
        }),
      });
    });
    await page.goto("/contacts");
    await expect(page.getByText("person@example.com")).toBeVisible();
    const verifyButton = page.locator('table button:has-text("Verify")').first();
    await expect(verifyButton).toBeVisible();
    await verifyButton.click();
    await expect(page.getByText(/^Verified /)).toBeVisible({ timeout: 10_000 });
  });

  test("contacts page exposes reusable list controls", async ({ page }) => {
    await page.route("**/api/v1/leads", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "lead-1",
            email: "person@example.com",
            first_name: "Test",
            last_name: "Lead",
            company: "Orbitworks",
            email_status: "unverified",
            verification_score: null,
            verification_integrity: null,
            last_verified_at: null,
            is_disposable: false,
            is_role_based: false,
            is_suppressed: false,
            verification_reasons: null,
            list_ids: [],
            list_names: [],
            created_at: "2026-04-08T10:00:00Z",
          },
        ]),
      });
    });
    await page.route("**/api/v1/lists", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          {
            id: "list-1",
            name: "Reusable Audience",
            description: "List",
            type: "static",
            created_at: "2026-04-08T10:00:00Z",
            updated_at: "2026-04-08T10:00:00Z",
            lead_count: 0,
            reachable_count: 0,
            risky_count: 0,
            invalid_count: 0,
            suppressed_count: 0,
            status_counts: {},
          },
        ]),
      });
    });
    await page.goto("/contacts");
    await expect(page.getByRole("button", { name: "Add selected to list" })).toBeVisible();
    await expect(page.getByRole("option", { name: "All lists" })).toBeAttached();
  });

  test("contacts detail can update contact type", async ({ page }) => {
    let lead = {
      id: "lead-1",
      email: "person@example.com",
      first_name: "Test",
      last_name: "Lead",
      company: "Orbitworks",
      contact_type: null,
      consent_status: "unknown",
      unsubscribe_status: "subscribed",
      engagement_score: 0,
      email_status: "unverified",
      verification_score: null,
      verification_integrity: null,
      last_verified_at: null,
      is_disposable: false,
      is_role_based: false,
      is_suppressed: false,
      verification_reasons: null,
      list_ids: [],
      list_names: [],
      created_at: "2026-04-08T10:00:00Z",
    };

    await page.route("**/api/v1/leads", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([lead]) });
    });
    await page.route("**/api/v1/lists", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.route("**/api/v1/leads/lead-1", async (route) => {
      lead = { ...lead, ...JSON.parse(route.request().postData() || "{}") };
      if (lead.contact_type === "mixed") lead.contact_type = null;
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(lead) });
    });

    await page.goto("/contacts");
    await page.getByRole("button", { name: "Details" }).click();
    await page.locator("select").filter({ has: page.getByRole("option", { name: "B2B" }) }).last().selectOption("b2b");
    await page.getByRole("button", { name: "Save" }).click();

    await expect(page.getByText("Updated person@example.com contact type to b2b.")).toBeVisible();
  });

  test("contacts bulk action can update selected lead contact type", async ({ page }) => {
    let leads = [
      {
        id: "lead-1",
        email: "one@example.com",
        first_name: "One",
        last_name: "Lead",
        company: "Orbitworks",
        contact_type: null,
        consent_status: "unknown",
        unsubscribe_status: "subscribed",
        engagement_score: 0,
        email_status: "unverified",
        verification_score: null,
        verification_integrity: null,
        last_verified_at: null,
        is_disposable: false,
        is_role_based: false,
        is_suppressed: false,
        verification_reasons: null,
        list_ids: [],
        list_names: [],
        created_at: "2026-04-08T10:00:00Z",
      },
      {
        id: "lead-2",
        email: "two@example.com",
        first_name: "Two",
        last_name: "Lead",
        company: "Orbitworks",
        contact_type: "b2b",
        consent_status: "unknown",
        unsubscribe_status: "subscribed",
        engagement_score: 0,
        email_status: "unverified",
        verification_score: null,
        verification_integrity: null,
        last_verified_at: null,
        is_disposable: false,
        is_role_based: false,
        is_suppressed: false,
        verification_reasons: null,
        list_ids: [],
        list_names: [],
        created_at: "2026-04-08T10:00:00Z",
      },
    ];

    await page.route("**/api/v1/leads", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(leads) });
    });
    await page.route("**/api/v1/lists", async (route) => {
      await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    });
    await page.route("**/api/v1/leads/bulk/contact-type", async (route) => {
      const payload = JSON.parse(route.request().postData() || "{}");
      leads = leads.map((lead) =>
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

    await page.goto("/contacts");
    await page.getByLabel("Select one@example.com").check();
    await page.getByLabel("Select two@example.com").check();
    await page.getByLabel("Bulk contact type").selectOption("b2c");
    await page.getByRole("button", { name: "Set contact type" }).click();

    await expect(page.getByText("Updated 2 leads to b2c.")).toBeVisible();
  });
});
