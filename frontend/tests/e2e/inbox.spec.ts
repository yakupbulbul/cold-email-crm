import { expect, test } from "@playwright/test";

test("inbox page renders real status and thread detail", async ({ page }) => {
  await page.route("**/api/v1/inbox/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sync_enabled: true,
        workers_enabled: true,
        worker_status: { status: "healthy", detail: "Background workers are running." },
        scheduler_status: { status: "healthy", detail: "Automatic inbox sync is running." },
        mailboxes: [
          {
            id: "mailbox-1",
            email: "support@example.com",
            display_name: "Support",
            status: "active",
            inbox_sync_enabled: true,
            inbox_sync_status: "healthy",
            inbox_last_synced_at: "2026-04-14T12:00:00",
            inbox_last_success_at: "2026-04-14T12:00:00",
            inbox_last_error: null,
            smtp_last_check_status: "healthy",
            imap_host: "imap.example.com",
            imap_port: 993,
          },
        ],
        configured_mailboxes_count: 1,
        sync_enabled_mailboxes_count: 1,
        healthy_mailboxes_count: 1,
        threads_count: 1,
        unread_threads_count: 1,
        messages_received_today: 1,
        last_sync_at: "2026-04-14T12:00:00",
        last_message_at: "2026-04-14T12:01:00",
        blockers: [],
      }),
    });
  });

  await page.route("**/api/v1/inbox/threads*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "thread-1",
          subject: "Re: Demo follow up",
          mailbox_id: "mailbox-1",
          mailbox_email: "support@example.com",
          contact_email: "buyer@example.com",
          contact_name: "Buyer",
          campaign_id: "campaign-1",
          campaign_name: "April Demo Push",
          contact_id: "contact-1",
          linkage_status: "linked",
          participants: ["buyer@example.com", "support@example.com"],
          status: "active",
          last_message_at: "2026-04-14T12:01:00",
          snippet: "Interested in a demo this week.",
          unread: true,
          unread_count: 1,
          last_message_direction: "inbound",
          last_message_preview: "Interested in a demo this week.",
        },
      ]),
    });
  });

  await page.route("**/api/v1/inbox/threads/thread-1", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "thread-1",
        subject: "Re: Demo follow up",
        mailbox_id: "mailbox-1",
        mailbox_email: "support@example.com",
        contact_email: "buyer@example.com",
        contact_name: "Buyer",
        campaign_id: "campaign-1",
        campaign_name: "April Demo Push",
        contact_id: "contact-1",
        linkage_status: "linked",
        participants: ["buyer@example.com", "support@example.com"],
        status: "active",
        last_message_at: "2026-04-14T12:01:00",
        snippet: "Interested in a demo this week.",
        unread: true,
        unread_count: 1,
        last_message_direction: "inbound",
        last_message_preview: "Interested in a demo this week.",
        messages: [
          {
            id: "message-1",
            thread_id: "thread-1",
            direction: "outbound",
            subject: "Demo follow up",
            body_text: "Checking in about the platform.",
            from_address: "support@example.com",
            to_address: "buyer@example.com",
            sent_at: "2026-04-14T11:55:00",
            is_read: true,
          },
          {
            id: "message-2",
            thread_id: "thread-1",
            direction: "inbound",
            subject: "Re: Demo follow up",
            body_text: "Interested in a demo this week.",
            from_address: "buyer@example.com",
            to_address: "support@example.com",
            sent_at: "2026-04-14T12:01:00",
            is_read: false,
          },
        ],
      }),
    });
  });

  await page.goto("/inbox");
  await page.waitForLoadState("networkidle");

  await expect(page.getByRole("heading", { name: "Inbox" })).toBeVisible();
  await expect(page.getByText("April Demo Push").first()).toBeVisible();
  await expect(page.getByText("Interested in a demo this week.")).toHaveCount(2);
  await expect(page.getByText("support@example.com", { exact: true }).last()).toBeVisible();
});

test("inbox empty state explains real blockers", async ({ page }) => {
  await page.route("**/api/v1/inbox/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        sync_enabled: false,
        workers_enabled: false,
        worker_status: { status: "disabled", detail: "Background workers are disabled." },
        scheduler_status: { status: "disabled", detail: "Automatic inbox sync is disabled." },
        mailboxes: [],
        configured_mailboxes_count: 0,
        sync_enabled_mailboxes_count: 0,
        healthy_mailboxes_count: 0,
        threads_count: 0,
        unread_threads_count: 0,
        messages_received_today: 0,
        last_sync_at: null,
        last_message_at: null,
        blockers: [
          { code: "no_mailboxes", message: "No mailboxes are configured for inbox sync yet." },
        ],
      }),
    });
  });

  await page.route("**/api/v1/inbox/threads*", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });

  await page.goto("/inbox");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText("No inbox threads yet")).toBeVisible();
  await expect(page.getByText("No mailboxes are configured for inbox sync yet.")).toBeVisible();
});
