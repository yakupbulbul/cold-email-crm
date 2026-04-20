import { test, expect } from "@playwright/test";

test("ops dashboard loads without crashing", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/ops");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: /ops command center/i })).toBeVisible({ timeout: 8_000 });
});

test("ops health status cards render", async ({ page }) => {
  await page.goto("/ops");
  await page.waitForLoadState("networkidle");
  await expect(page.getByText("Core Database")).toBeVisible();
  await expect(page.getByText("Redis Backplane")).toBeVisible();
  await expect(page.getByText("Background Workers")).toBeVisible();
  await expect(page.getByText("SMTP/IMAP Infrastructure")).toBeVisible();
});

test("ops/jobs page loads and table renders", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/ops/jobs");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("ops/alerts page loads", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/ops/alerts");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("ops/deliverability page loads and KPI cards render", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/ops/deliverability");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("ops/readiness page loads and checklist renders", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/ops/readiness");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1, h2").first()).toBeVisible({ timeout: 8_000 });
});

test("settings page reflects real backend-driven ops state", async ({ page }) => {
  await page.goto("/settings");
  await page.waitForLoadState("networkidle");
  await expect(page.getByRole("heading", { name: /system settings/i })).toBeVisible();
  await expect(page.getByText("Global configuration portal is under construction")).toHaveCount(0);
  await expect(page.getByText("http://127.0.0.1:8060")).toBeVisible();
  await expect(page.getByText(/mailcow integration is configured and reachable/i).first()).toBeVisible();
  await expect(page.getByText(/background workers are (disabled in lean development mode|enabled and available)/i).first()).toBeVisible();
});
