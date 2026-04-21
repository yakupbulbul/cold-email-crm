import { test, expect } from "@playwright/test";

const now = "2026-04-21T10:00:00Z";

type MockTask = {
  id: string;
  title: string;
  description?: string | null;
  status: string;
  priority: string;
  category: string;
  due_at?: string | null;
  related_entity_type?: string | null;
  related_entity_id?: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

test("command center renders tasks timeline notes and runbooks", async ({ page }) => {
  let tasks: MockTask[] = [
    {
      id: "task-1",
      title: "Test campaign retry",
      description: "Confirm worker consumes the next pass.",
      status: "todo",
      priority: "high",
      category: "campaign",
      due_at: now,
      related_entity_type: "campaign",
      related_entity_id: "campaign-1",
      metadata: {},
      created_at: now,
      updated_at: now,
    },
  ];
  const actions = [
    {
      id: "action-1",
      action_type: "campaign_dry_run",
      source: "campaigns",
      result: "success",
      message: "Campaign dry run completed: 9 April Test",
      related_entity_type: "campaign",
      related_entity_id: "campaign-1",
      metadata: {},
      created_at: now,
    },
  ];
  const runbooks = [
    {
      id: "runbook-1",
      name: "Campaign launch checklist",
      description: "Safe campaign launch sequence.",
      category: "campaign",
      is_active: true,
      steps: [
        {
          id: "step-1",
          runbook_id: "runbook-1",
          step_order: 1,
          title: "Run dry-run",
          default_status: "todo",
          created_at: now,
          updated_at: now,
        },
      ],
      created_at: now,
      updated_at: now,
    },
  ];

  await page.route("**/api/v1/command-center/summary", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        today_tasks: tasks,
        overdue_tasks: [],
        blocked_tasks: [],
        recent_actions: actions,
        stats: { todo: tasks.length, in_progress: 0, blocked: 0, done_today: 0, actions_today: actions.length },
      }),
    });
  });
  await page.route("**/api/v1/command-center/tasks**", async (route) => {
    if (route.request().method() === "POST") {
      const payload = JSON.parse(route.request().postData() || "{}");
      tasks = [
        ...tasks,
        {
          id: "task-2",
          title: payload.title,
          description: payload.description,
          status: payload.status || "todo",
          priority: payload.priority || "normal",
          category: payload.category || "manual",
          due_at: payload.due_at,
          related_entity_type: null,
          related_entity_id: null,
          metadata: {},
          created_at: now,
          updated_at: now,
        },
      ];
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(tasks[tasks.length - 1]) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(tasks) });
  });
  await page.route("**/api/v1/command-center/actions**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(actions) });
  });
  await page.route("**/api/v1/command-center/daily-notes**", async (route) => {
    if (route.request().method() === "POST") {
      const payload = JSON.parse(route.request().postData() || "{}");
      await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "note-1", note_date: payload.note_date, content: payload.content, created_at: now, updated_at: now }) });
      return;
    }
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ id: "note-1", note_date: "2026-04-21", content: "Inbox sync tested.", created_at: now, updated_at: now }]) });
  });
  await page.route("**/api/v1/command-center/runbooks**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(runbooks) });
  });

  await page.goto("/command-center");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: /command center/i })).toBeVisible();
  await expect(page.getByText("Test campaign retry")).toBeVisible();
  await expect(page.getByText("Campaign dry run completed: 9 April Test")).toBeVisible();
  await expect(page.getByText("Inbox sync tested.")).toBeVisible();
  await expect(page.getByText("Campaign launch checklist")).toBeVisible();

  await page.getByPlaceholder(/add a task/i).fill("Check provider OAuth");
  await page.getByRole("button", { name: /add/i }).click();
  await expect(page.getByText("Task created.")).toBeVisible();
});

test("command center shows useful empty states", async ({ page }) => {
  await page.route("**/api/v1/command-center/summary", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ today_tasks: [], overdue_tasks: [], blocked_tasks: [], recent_actions: [], stats: { todo: 0, in_progress: 0, blocked: 0, done_today: 0, actions_today: 0 } }),
    });
  });
  await page.route("**/api/v1/command-center/tasks**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
  await page.route("**/api/v1/command-center/actions**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
  await page.route("**/api/v1/command-center/daily-notes**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });
  await page.route("**/api/v1/command-center/runbooks**", async (route) => {
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([]) });
  });

  await page.goto("/command-center");
  await expect(page.getByText("No active tasks yet")).toBeVisible();
  await expect(page.getByText("No runbooks yet")).toBeVisible();
  await expect(page.getByText("No operational actions logged yet")).toBeVisible();
});
