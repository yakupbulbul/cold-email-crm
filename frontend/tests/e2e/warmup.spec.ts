import { expect, test } from "@playwright/test";

test("warmup page renders real backend status, pairs, and logs", async ({ page }) => {
  await page.route("**/api/v1/warmup/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        global_status: "enabled",
        worker_status: { status: "healthy", detail: "Background workers are running." },
        scheduler_status: { status: "healthy", detail: "Warm-up scheduler is queuing jobs on the expected cadence." },
        inboxes_warming_count: 2,
        eligible_mailboxes_count: 2,
        active_pairs_count: 2,
        successful_sends_today: 4,
        failed_sends_today: 1,
        health_percent: 80,
        blockers: [],
        last_run_at: "2026-04-12T08:00:00Z",
        next_run_at: "2026-04-12T08:15:00Z",
        mailboxes: [
          {
            id: "mailbox-a",
            email: "a@example.com",
            display_name: "A",
            warmup_enabled: true,
            warmup_status: "ready",
            warmup_last_checked_at: "2026-04-12T08:01:00Z",
            warmup_last_result: "success",
            warmup_block_reason: null,
            smtp_last_check_status: "healthy",
            smtp_last_check_message: "SMTP delivery succeeded.",
            status: "active",
            current_warmup_stage: 1,
          },
          {
            id: "mailbox-b",
            email: "b@example.com",
            display_name: "B",
            warmup_enabled: true,
            warmup_status: "ready",
            warmup_last_checked_at: "2026-04-12T08:01:00Z",
            warmup_last_result: "success",
            warmup_block_reason: null,
            smtp_last_check_status: "healthy",
            smtp_last_check_message: "SMTP delivery succeeded.",
            status: "active",
            current_warmup_stage: 1,
          },
        ],
      }),
    });
  });
  await page.route("**/api/v1/warmup/pairs", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "pair-1",
          sender_mailbox_id: "mailbox-a",
          recipient_mailbox_id: "mailbox-b",
          sender_email: "a@example.com",
          recipient_email: "b@example.com",
          state: "active",
          last_send_at: "2026-04-12T08:00:00Z",
          next_scheduled_at: "2026-04-12T08:15:00Z",
          last_result: "success",
          last_error: null,
          daily_sent_count: 2,
          daily_limit: 5,
        },
      ]),
    });
  });
  await page.route("**/api/v1/warmup/logs?limit=50", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          id: "log-1",
          sender_mailbox_id: "mailbox-a",
          recipient_mailbox_id: "mailbox-b",
          sender_email: "a@example.com",
          recipient_email: "b@example.com",
          timestamp: "2026-04-12T08:00:00Z",
          event_type: "send",
          status: "success",
          error_category: null,
          result_detail: "Warm-up email sent successfully.",
          target_email: "b@example.com",
        },
      ]),
    });
  });

  await page.goto("/warmup");

  await expect(page.getByText("Warm-up Engine")).toBeVisible();
  await expect(page.getByText("80%")).toBeVisible();
  await expect(page.getByText("Total Sent Today").locator("..").getByText("4", { exact: true })).toBeVisible();
  await expect(page.getByRole("cell", { name: "a@example.com" }).first()).toBeVisible();
  await expect(page.getByRole("cell", { name: "b@example.com" }).first()).toBeVisible();
  await expect(page.getByText("Warm-up email sent successfully.")).toBeVisible();
});

test("warmup page calls real start and pause actions and refreshes state", async ({ page }) => {
  let globalStatus: "paused" | "enabled" = "paused";

  await page.route("**/api/v1/warmup/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        global_status: globalStatus,
        worker_status: { status: "healthy", detail: "Background workers are running." },
        scheduler_status: { status: "healthy", detail: "Warm-up scheduler is queuing jobs on the expected cadence." },
        inboxes_warming_count: 2,
        eligible_mailboxes_count: 2,
        active_pairs_count: globalStatus === "enabled" ? 2 : 0,
        successful_sends_today: 0,
        failed_sends_today: 0,
        health_percent: null,
        blockers: globalStatus === "enabled" ? [] : [{ code: "warmup_paused", message: "Warm-up is paused globally." }],
        last_run_at: null,
        next_run_at: globalStatus === "enabled" ? "2026-04-12T08:15:00Z" : null,
        mailboxes: [],
      }),
    });
  });
  await page.route("**/api/v1/warmup/pairs", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/warmup/logs?limit=50", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/warmup/start", async (route) => {
    globalStatus = "enabled";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "enabled",
        detail: "Warm-up enabled globally and an immediate warm-up cycle was queued.",
        job_queued: true,
        job_id: "warmup-job-1",
      }),
    });
  });
  await page.route("**/api/v1/warmup/pause", async (route) => {
    globalStatus = "paused";
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "paused",
        detail: "Warm-up paused globally. Active pairs remain configured but will not be processed until warm-up is started again.",
      }),
    });
  });

  await page.goto("/warmup");

  await page.getByRole("button", { name: "Start Warm-up" }).click();
  await expect(page.getByText("Warm-up enabled globally and an immediate warm-up cycle was queued.")).toBeVisible();
  await expect(page.getByText("No warm-up blockers are active right now.")).toBeVisible();

  await page.getByRole("button", { name: "Pause All" }).click();
  await expect(page.getByText("Warm-up paused globally. Active pairs remain configured but will not be processed until warm-up is started again.")).toBeVisible();
  await expect(page.locator(".rounded-xl.border.border-amber-200.bg-amber-50").getByText("Warm-up is paused globally.")).toBeVisible();
});

test("warmup page toggles mailbox participation and surfaces honest blockers", async ({ page }) => {
  let enabled = false;

  await page.route("**/api/v1/warmup/status", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        global_status: "enabled",
        worker_status: { status: "healthy", detail: "Background workers are running." },
        scheduler_status: { status: "stale", detail: "Warm-up scheduler activity is stale. Automatic warm-up passes are not being queued on time." },
        inboxes_warming_count: enabled ? 1 : 0,
        eligible_mailboxes_count: 0,
        active_pairs_count: 0,
        successful_sends_today: 0,
        failed_sends_today: 0,
        health_percent: null,
        blockers: [
          { code: "scheduler_unhealthy", message: "Warm-up scheduler activity is stale. Automatic warm-up passes are not being queued on time." },
          { code: "insufficient_mailboxes", message: "At least 2 SMTP-healthy warm-up-enabled mailboxes are required." },
        ],
        last_run_at: null,
        next_run_at: null,
        mailboxes: [
          {
            id: "mailbox-a",
            email: "a@example.com",
            display_name: "A",
            warmup_enabled: enabled,
            warmup_status: enabled ? "blocked" : "disabled",
            warmup_last_checked_at: "2026-04-12T08:01:00Z",
            warmup_last_result: "failed",
            warmup_block_reason: enabled ? "SMTP check has not been run." : null,
            smtp_last_check_status: null,
            smtp_last_check_message: null,
            status: "active",
            current_warmup_stage: 1,
          },
        ],
      }),
    });
  });
  await page.route("**/api/v1/warmup/pairs", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/warmup/logs?limit=50", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await page.route("**/api/v1/mailboxes/mailbox-a/warmup", async (route) => {
    enabled = true;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        id: "mailbox-a",
        domain_id: "domain-1",
        email: "a@example.com",
        display_name: "A",
        smtp_host: "smtp.example.com",
        smtp_port: 587,
        smtp_security_mode: "starttls",
        imap_host: "imap.example.com",
        imap_port: 993,
        warmup_enabled: true,
        warmup_status: "blocked",
        warmup_last_checked_at: "2026-04-12T08:01:00Z",
        warmup_last_result: "failed",
        warmup_block_reason: "SMTP check has not been run.",
        daily_send_limit: 50,
        current_warmup_stage: 1,
        status: "active",
        remote_mailcow_provisioned: false,
        provisioning_mode: "local_only",
        created_at: "2026-04-12T08:00:00Z",
      }),
    });
  });

  await page.goto("/warmup");

  await expect(page.getByText("At least 2 SMTP-healthy warm-up-enabled mailboxes are required.")).toBeVisible();
  await page.getByRole("button", { name: "Enable warm-up" }).click();
  await expect(page.getByText("Mailbox added to warm-up participation.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Disable warm-up" })).toBeVisible();
  await expect(page.getByText("SMTP check has not been run.")).toBeVisible();
});
