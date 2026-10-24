import assert from "node:assert/strict";
import { chromium } from "playwright";

const browser = await chromium.launch({ headless: true, executablePath: "C:/Program Files/Google/Chrome/Application/chrome.exe" });
try {
  const page = await browser.newPage({ viewport: { width: 1365, height: 900 } });
  await page.goto("http://localhost:3001", { waitUntil: "networkidle" });
  await assert.doesNotReject(() => page.getByRole("heading", { name: /the small promises/i }).waitFor());
  await page.getByRole("button", { name: "Import notes" }).click();
  await page.getByRole("heading", { name: /drop the conversation/i }).waitFor();
  await page.getByRole("button", { name: "Privacy" }).click();
  await page.getByRole("heading", { name: /your conversations are yours/i }).waitFor();
  await page.setViewportSize({ width: 390, height: 844 });
  assert.ok(await page.locator("body").evaluate(el => el.scrollWidth <= window.innerWidth), "mobile layout should not overflow horizontally");
  await page.emulateMedia({ colorScheme: "dark" });
  assert.equal(await page.locator("body").evaluate(el => getComputedStyle(el).backgroundColor), "rgb(23, 29, 25)", "system dark mode should apply the dark canvas");
  console.log("Playwright UI smoke passed: dashboard, import, privacy, mobile width, dark mode.");
} finally {
  await browser.close();
}
