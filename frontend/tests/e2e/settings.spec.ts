import { expect, test } from "@playwright/test";

test("settings page shows real backend-driven runtime state", async ({ page }) => {
  const seenRequests = new Set<string>();

  page.on("request", (request) => {
    seenRequests.add(request.url());
  });

  await page.goto("/settings");

  await expect(page.getByRole("heading", { name: "System Settings" })).toBeVisible();
  await expect(page.getByText("Global configuration portal is under construction")).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "Application Environment" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Mailcow Integration" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Worker / Queue Mode" })).toBeVisible();
  await expect(page.getByText("Bootstrap Admin").first()).toBeVisible();
  await expect(page.getByText("http://127.0.0.1:8060")).toBeVisible();
  await expect(page.getByText("Read only").first()).toBeVisible();

  const crossOriginRequests = [...seenRequests].filter(
    (url) =>
      !url.startsWith("http://localhost:3010") &&
      !url.startsWith("data:") &&
      !url.startsWith("blob:"),
  );

  expect(crossOriginRequests).toEqual([]);
});
