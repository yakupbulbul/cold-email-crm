import { expect, test } from "@playwright/test";

test("send email page submits a real backend-driven send request and shows logs", async ({ page }) => {
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "mailbox-1",
          email: "sender@example.com",
          display_name: "Sender",
          status: "active",
          daily_send_limit: 50,
          current_warmup_stage: 0,
          warmup_enabled: false,
          remote_mailcow_provisioned: true,
          provisioning_mode: "mailcow_synced",
          created_at: "2026-04-09T10:00:00Z",
        },
      ]),
    });
  });

  let sendLog = {
    id: "log-1",
    target_email: "existing@example.com",
    subject: "Older send",
    delivery_status: "success",
    smtp_response: "<older-message-id@example.com>",
    created_at: "2026-04-09T10:00:00Z",
  };

  await page.route("**/api/v1/send-email/logs?limit=20", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([sendLog]),
    });
  });

  await page.route("**/api/v1/send-email", async (route) => {
    sendLog = {
      id: "log-2",
      target_email: "recipient@example.com",
      subject: "Test email",
      delivery_status: "success",
      smtp_response: "<message-id@example.com>",
      created_at: "2026-04-09T11:00:00Z",
    };
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        success: true,
        status: "sent",
        message_id: "<message-id@example.com>",
        provider: "smtp",
        log_id: "log-2",
      }),
    });
  });

  await page.goto("/send-email");
  await page.locator("#send-email-to").fill("recipient@example.com");
  await page.getByRole("button", { name: "Send Email" }).click();

  await expect(page.getByText("Email sent through smtp.")).toBeVisible();
  await expect(page.locator("span.font-mono")).toContainText("<message-id@example.com>");
  await expect(page.getByText("recipient@example.com")).toBeVisible();
});

test("send email page shows honest backend errors", async ({ page }) => {
  await page.route("**/api/v1/mailboxes", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "mailbox-1",
          email: "sender@example.com",
          display_name: "Sender",
          status: "paused",
          daily_send_limit: 50,
          current_warmup_stage: 0,
          warmup_enabled: false,
          remote_mailcow_provisioned: false,
          provisioning_mode: "local_only",
          created_at: "2026-04-09T10:00:00Z",
        },
      ]),
    });
  });
  await page.route("**/api/v1/send-email/logs?limit=20", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/send-email", async (route) => {
    await route.fulfill({
      status: 409,
      contentType: "application/json",
      body: JSON.stringify({
        detail: {
          message: "Mailbox must be active before sending email.",
          category: "mailbox_inactive",
        },
      }),
    });
  });

  await page.goto("/send-email");
  await page.locator("#send-email-to").fill("recipient@example.com");
  await page.getByRole("button", { name: "Send Email" }).click();

  await expect(page.getByText("Send failed")).toBeVisible();
  await expect(page.getByText("Mailbox must be active before sending email.")).toBeVisible();
});
