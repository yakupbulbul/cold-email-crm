import { expect, test } from "@playwright/test";

test("frontend stays on the local backend boundary and runtime responses are secret-safe", async ({ page }) => {
  const seenRequests = new Set<string>();

  page.on("request", (request) => {
    seenRequests.add(request.url());
  });

  for (const route of ["/settings", "/domains", "/mailboxes", "/ops"]) {
    await page.goto(route);
    await page.waitForLoadState("networkidle");
  }

  const token = await page.evaluate(() => window.localStorage.getItem("token"));
  expect(token).toBeTruthy();

  const settingsSummary = await page.evaluate(async (authToken) => {
    const response = await fetch("/api/v1/settings/summary", {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    return response.json();
  }, token);
  const mailboxes = await page.evaluate(async (authToken) => {
    const response = await fetch("/api/v1/mailboxes", {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    return response.json();
  }, token);

  const serializedSettings = JSON.stringify(settingsSummary);
  const serializedMailboxes = JSON.stringify(mailboxes);

  for (const forbidden of [
    "MAILCOW_API_KEY",
    "SECRET_KEY",
    "access_token",
    "smtp_password",
    "imap_password",
    "smtp_password_encrypted",
    "imap_password_encrypted",
  ]) {
    expect(serializedSettings).not.toContain(forbidden);
    expect(serializedMailboxes).not.toContain(forbidden);
  }

  expect(settingsSummary.frontend_mailcow_direct_access).toBe(false);
  expect(Array.isArray(mailboxes)).toBe(true);

  const crossOriginRequests = [...seenRequests].filter(
    (url) =>
      !url.startsWith("http://localhost:3010") &&
      !url.startsWith("data:") &&
      !url.startsWith("blob:"),
  );

  expect(crossOriginRequests).toEqual([]);
});
