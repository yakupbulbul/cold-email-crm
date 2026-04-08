import { expect, test } from "@playwright/test";

test("mailbox, suppression, and campaign create flows work in no-seed mode", async ({ page }) => {
  const suffix = Date.now().toString();
  const mailboxLocalPart = `ui${suffix}`;
  const suppressionEmail = `ui-${suffix}@example.com`;
  const campaignName = `UI Campaign ${suffix}`;
  const seenRequests = new Set<string>();

  page.on("request", (request) => {
    seenRequests.add(request.url());
  });

  await page.goto("/mailboxes");
  await page.selectOption('[data-testid="mailbox-domain-select"]', { index: 1 });
  await page.fill('[data-testid="mailbox-local-part-input"]', mailboxLocalPart);
  await page.fill('[data-testid="mailbox-display-name-input"]', "UI Mailbox");
  await page.fill('[data-testid="mailbox-password-input"]', "local-password-123");
  await page.click('[data-testid="create-mailbox-button"]');
  await expect(page.locator(`text=${mailboxLocalPart}`)).toBeVisible();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator(`text=${mailboxLocalPart}`)).toBeVisible();

  await page.goto("/suppression");
  await page.fill('[data-testid="suppression-email-input"]', suppressionEmail);
  await page.fill('[data-testid="suppression-reason-input"]', "bounce");
  await page.click('[data-testid="create-suppression-button"]');
  await expect(page.locator(`text=${suppressionEmail}`)).toBeVisible();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator(`text=${suppressionEmail}`)).toBeVisible();

  await page.goto("/campaigns");
  await page.fill('[data-testid="campaign-name-input"]', campaignName);
  await page.selectOption('[data-testid="campaign-mailbox-select"]', { index: 1 });
  await page.fill('[data-testid="campaign-subject-input"]', "Hello from UI");
  await page.fill('[data-testid="campaign-body-input"]', "Body from UI");
  await page.fill('[data-testid="campaign-daily-limit-input"]', "42");
  await page.click('[data-testid="create-campaign-button"]');
  await expect(page.locator(`text=${campaignName}`)).toBeVisible();
  await page.reload({ waitUntil: "domcontentloaded" });
  await expect(page.locator(`text=${campaignName}`)).toBeVisible();

  const crossOriginRequests = [...seenRequests].filter(
    (url) => !url.startsWith("http://localhost:3010") && !url.startsWith("data:"),
  );
  expect(crossOriginRequests).toEqual([]);
});
