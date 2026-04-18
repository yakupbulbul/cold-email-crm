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
  await expect(page.getByTestId("mailbox-mode-message")).toContainText(
    /Safe mode stores the Mailcow mailbox locally only|Mutation mode creates the mailbox in Mailcow and CRM together|Google Workspace mailboxes use backend-only OAuth/i,
  );
});

test("mailbox row actions render when mailboxes exist", async ({ page }) => {
  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");
  const editButtons = page.locator('[data-testid^="edit-mailbox-"]');
  const deleteButtons = page.locator('[data-testid^="delete-mailbox-"]');
  const checkButtons = page.locator('[data-testid^="check-smtp-mailbox-"]');
  if ((await editButtons.count()) > 0) {
    await expect(editButtons.first()).toBeVisible();
    await expect(deleteButtons.first()).toBeVisible();
    await expect(checkButtons.first()).toBeVisible();
    await expect(page.getByText(/Mailcow synced|Local only/).first()).toBeVisible();
  } else {
    await expect(page.getByText("No Mailboxes Found")).toBeVisible();
  }
});

test("google workspace mailbox shows connect controls and callback success state", async ({ page }) => {
  await page.route("**/api/v1/settings/summary", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        default_provider: "google_workspace",
        enabled_providers: ["mailcow", "google_workspace"],
        mailcow_mutations_enabled: false,
      }),
    });
  });

  await page.route("**/api/v1/domains", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route("**/api/v1/mailboxes/mailbox-google/provider-check", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        provider_type: "google_workspace",
        status: "healthy",
        smtp: { status: "healthy", category: "ok", message: "SMTP authenticated successfully." },
        imap: { status: "healthy", category: "ok", message: "IMAP authenticated successfully." },
      }),
    });
  });

  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "mailbox-google",
          domain_id: "domain-1",
          email: "info@learnoapp.com",
          display_name: "Info",
          provider_type: "google_workspace",
          provider_status: "active",
          provider_config_status: "configured",
          smtp_host: "smtp.gmail.com",
          smtp_port: 587,
          smtp_security_mode: "starttls",
          imap_host: "imap.gmail.com",
          imap_port: 993,
          imap_security_mode: "ssl",
          oauth_enabled: true,
          oauth_provider: "google_workspace",
          oauth_connection_status: "not_connected",
          oauth_last_checked_at: null,
          oauth_last_error: null,
          external_account_email: null,
          warmup_enabled: false,
          inbox_sync_enabled: true,
          daily_send_limit: 50,
          current_warmup_stage: 1,
          status: "active",
          remote_mailcow_provisioned: false,
          provisioning_mode: "local_only",
          created_at: new Date().toISOString(),
        },
      ]),
    });
  });

  await page.goto("/mailboxes?mailbox_id=mailbox-google&oauth_status=connected&oauth_message=Google%20Workspace%20connected");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText(/Google Workspace connected|Provider diagnostics completed/i)).toBeVisible();
  await expect(page.getByTestId("connect-google-mailbox-mailbox-google")).toBeVisible();
  await expect(page.getByTestId("provider-check-google-mailbox-mailbox-google")).toBeVisible();
});

test("connected google workspace mailbox shows reconnect and disconnect controls", async ({ page }) => {
  await page.route("**/api/v1/settings/summary", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        default_provider: "google_workspace",
        enabled_providers: ["mailcow", "google_workspace"],
        mailcow_mutations_enabled: false,
      }),
    });
  });

  await page.route("**/api/v1/domains", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "mailbox-google",
          domain_id: "domain-1",
          email: "info@learnoapp.com",
          display_name: "Info",
          provider_type: "google_workspace",
          provider_status: "active",
          provider_config_status: "configured",
          smtp_host: "smtp.gmail.com",
          smtp_port: 587,
          smtp_security_mode: "starttls",
          imap_host: "imap.gmail.com",
          imap_port: 993,
          imap_security_mode: "ssl",
          oauth_enabled: true,
          oauth_provider: "google_workspace",
          oauth_connection_status: "connected",
          oauth_last_checked_at: new Date().toISOString(),
          oauth_last_error: null,
          external_account_email: "info@learnoapp.com",
          last_provider_check_at: new Date().toISOString(),
          last_provider_check_message: "Provider diagnostics completed.",
          warmup_enabled: false,
          inbox_sync_enabled: true,
          daily_send_limit: 50,
          current_warmup_stage: 1,
          status: "active",
          remote_mailcow_provisioned: false,
          provisioning_mode: "local_only",
          created_at: new Date().toISOString(),
        },
      ]),
    });
  });

  await page.goto("/mailboxes");
  await page.waitForLoadState("networkidle");

  await expect(page.getByTestId("reconnect-google-mailbox-mailbox-google")).toBeVisible();
  await expect(page.getByTestId("disconnect-google-mailbox-mailbox-google")).toBeVisible();
  await expect(page.getByTestId("provider-check-google-mailbox-mailbox-google")).toBeVisible();
});
