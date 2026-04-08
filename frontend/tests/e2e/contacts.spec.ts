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
    await expect(page.getByText("Unknown")).toHaveCount(0);
  });

  test("contacts detail area opens", async ({ page }) => {
    await page.goto("/contacts");
    const buttonTexts = (await page.locator("button").allTextContents()).map((value) => value.trim());
    const detailsIndex = buttonTexts.findIndex((value) => value === "Details");
    if (detailsIndex >= 0) {
      const detailsButton = page.locator("button").nth(detailsIndex);
      await expect(detailsButton).toBeVisible();
      await detailsButton.click();
      await expect(page.getByText("Latest verification state for this lead.")).toBeVisible();
    } else {
      await expect(page.getByText("No leads available")).toBeVisible();
    }
  });

  test("verify actions surface real backend progress", async ({ page }) => {
    await page.goto("/contacts");

    const buttonTexts = (await page.locator("button").allTextContents()).map((value) => value.trim());
    const verifyIndex = buttonTexts.findIndex((value) => value === "Verify");
    if (verifyIndex >= 0) {
      const verifyButton = page.locator("button").nth(verifyIndex);
      await expect(verifyButton).toBeVisible();
      await verifyButton.click();
      await expect(page.getByText(/^Verified /)).toBeVisible({ timeout: 10_000 });
    } else {
      await expect(page.getByText("No leads available")).toBeVisible();
    }
  });
});
