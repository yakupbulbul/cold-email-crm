import { test, expect } from "@playwright/test";

test("ops dashboard loads without crashing", async ({ page }) => {
  page.on("pageerror", (err) => { throw err; });
  await page.goto("/ops");
  await page.waitForLoadState("networkidle");
  await expect(page.locator("h1").first()).toBeVisible({ timeout: 8_000 });
});

test("ops health status cards render", async ({ page }) => {
  await page.goto("/ops");
  await page.waitForLoadState("networkidle");
  // At least 2 status cards from the grid
  const cards = page.locator(".rounded-2xl, .card, article");
  await expect(cards.first()).toBeVisible({ timeout: 8_000 });
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
