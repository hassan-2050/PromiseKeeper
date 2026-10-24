import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { chromium } from "playwright";

const WEB = process.env.TEST_WEB_URL || "http://localhost:3001";
const API = process.env.TEST_API_URL || "http://localhost:9000/api";
const name = `Synthetic UI check ${Date.now()}`;
const notes =
  "SYNTHETIC UI TEST - No real conversation.\n\nRina: I will send the launch checklist by 2030-11-20.";
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const context = await browser.newContext({
  viewport: { width: 1365, height: 960 },
  permissions: ["clipboard-read", "clipboard-write"],
});
const page = await context.newPage();
page.setDefaultTimeout(15000);
const errors = [];
page.on("pageerror", (error) => errors.push(error.message));
let sourceId;
const nav = (view) =>
  page
    .getByRole("navigation", { name: "Workspace navigation", exact: true })
    .getByRole("button", { name: view, exact: true })
    .click();

try {
  await page.goto(WEB, { waitUntil: "networkidle" });
  await page.locator(".loading-state").waitFor({ state: "hidden" });
  await page.getByRole("heading", { name: /Less chasing/ }).waitFor();
  const help = page.getByRole("button", { name: "Help", exact: true });
  await help.click();
  await page.getByRole("dialog", { name: /Keep the context close/ }).waitFor();
  await page.keyboard.press("Escape");
  assert.equal(
    await help.evaluate((element) => element === document.activeElement),
    true,
    "help restores keyboard focus",
  );

  await page.locator(".sidebar-add").click();
  const fileInput = page.getByLabel("Choose a text file", { exact: true });
  await fileInput.setInputFiles({
    name: "synthetic-notes.md",
    mimeType: "text/markdown",
    buffer: Buffer.from(notes),
  });
  assert.equal(
    await page.locator("#import-box").inputValue(),
    notes,
    "file input is reviewable before extraction",
  );
  await page.getByLabel(/^Source name/).fill(name);
  await page.locator('input[type="datetime-local"]').fill("2026-10-21T09:00");
  const imported = page.waitForResponse(
    (response) =>
      response.url() === `${API}/import` &&
      response.request().method() === "POST",
    { timeout: 240000 },
  );
  await page
    .getByRole("button", { name: "Find the promises", exact: true })
    .click();
  const response = await imported;
  assert.equal(
    response.status(),
    200,
    "genuine local model import should succeed",
  );
  const result = await response.json();
  sourceId = result.source_id;
  assert.ok(result.count >= 1, "real extraction finds the explicit promise");
  const extracted = result.commitments.find((item) =>
    /launch checklist/i.test(item.evidence),
  );
  assert.ok(extracted, "the extracted item retains the test's source evidence");
  await page
    .getByRole("heading", { name: "Review inbox", exact: true })
    .waitFor();
  await page
    .getByLabel("Search promises", { exact: true })
    .fill("launch checklist");
  const card = page.locator(`article[data-commitment-id="${extracted.id}"]`);
  await card.waitFor();
  assert.match(
    await card.locator(".evidence").innerText(),
    /I will send the launch checklist by 2030-11-20/,
  );
  await card.locator("summary").click();
  await card.getByText(/Paragraph \d+.*characters/).waitFor();

  await card.getByRole("button", { name: "Edit", exact: true }).click();
  await card.getByLabel("Owner", { exact: true }).fill("Rina Patel");
  await card.getByLabel("Due date", { exact: true }).fill("Friday");
  await card.getByRole("button", { name: "Save edits", exact: true }).click();
  await card.getByRole("alert").waitFor();
  await card.getByLabel("Due date", { exact: true }).fill("2030-11-21");
  await card
    .getByLabel("Private note", { exact: true })
    .fill("Check after the lab meeting.");
  await card.getByRole("button", { name: "Save edits", exact: true }).click();
  await card.getByText("Rina Patel", { exact: true }).waitFor();
  assert.match(
    await card.locator(".private-note").innerText(),
    /Check after the lab meeting/,
  );
  await card.getByRole("button", { name: "Looks right", exact: true }).click();
  await card.waitFor({ state: "hidden" });
  await page.getByLabel("Status", { exact: true }).selectOption("confirmed");
  await card.waitFor();
  await card
    .getByRole("button", { name: "Draft follow-up", exact: true })
    .click();
  const draft = page.locator("#followup-text");
  await draft.waitFor();
  const initialDraft = await draft.inputValue();
  assert.match(initialDraft, /Hi Rina Patel/);
  assert.match(initialDraft, /2030-11-21/);
  const editedDraft = initialDraft + "\nP.S. A quick update is enough.";
  await draft.fill(editedDraft);
  await page.getByRole("button", { name: "Copy draft", exact: true }).click();
  assert.equal(
    (await page.evaluate(() => navigator.clipboard.readText())).replace(
      /\r\n/g,
      "\n",
    ),
    editedDraft,
  );
  const downloadedText = page.waitForEvent("download");
  await page
    .getByRole("button", { name: "Download text", exact: true })
    .click();
  const textDownload = await downloadedText;
  assert.equal(await readFile(await textDownload.path(), "utf8"), editedDraft);

  await nav("Timeline");
  await card.waitFor();
  assert.match(await card.locator(".due-label").innerText(), /Nov 21, 2030/);
  await nav("Privacy");
  const csvEvent = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export CSV", exact: true }).click();
  const csvDownload = await csvEvent;
  const csv = await readFile(await csvDownload.path(), "utf8");
  assert.match(csv, /Rina Patel/);
  assert.match(csv, /2030-11-21/);
  assert.match(csv, /source_name/);

  await nav("Timeline");
  await card.getByRole("button", { name: /Mark .* complete/ }).click();
  await card.waitFor({ state: "hidden" });
  await nav("Review inbox");
  await page.getByLabel("Status", { exact: true }).selectOption("complete");
  await page
    .getByLabel("Search promises", { exact: true })
    .fill("launch checklist");
  await card.waitFor();
  assert.match(await card.locator(".status-badge").innerText(), /Complete/);

  await nav("Privacy");
  await page.getByRole("button", { name: "Manage data", exact: true }).click();
  const source = page.locator(".source-row").filter({ hasText: name });
  await source
    .getByRole("button", { name: `Delete ${name}`, exact: true })
    .click();
  await source.getByRole("button", { name: "Keep it", exact: true }).click();
  assert.equal(
    await source.isVisible(),
    true,
    "cancelling deletion keeps the source",
  );
  await source
    .getByRole("button", { name: `Delete ${name}`, exact: true })
    .click();
  await source
    .getByRole("button", { name: "Delete source", exact: true })
    .click();
  await source.waitFor({ state: "hidden" });
  sourceId = undefined;

  await page.locator(".sidebar-add").click();
  assert.equal(
    await page.locator('input[type="datetime-local"]').inputValue(),
    "",
    "a new import does not reuse the previous source timestamp",
  );

  await page.setViewportSize({ width: 390, height: 844 });
  const openMenu = page.getByRole("button", {
    name: "Open navigation",
    exact: true,
  });
  await openMenu.click();
  const drawer = page.getByRole("dialog", {
    name: "Workspace navigation",
    exact: true,
  });
  await drawer.waitFor();
  await page.waitForFunction(() =>
    document.querySelector(".sidebar")?.contains(document.activeElement),
  );
  await page.keyboard.press("Shift+Tab");
  assert.equal(
    await drawer.evaluate((element) =>
      element.contains(document.activeElement),
    ),
    true,
    "drawer traps keyboard focus",
  );
  await page.keyboard.press("Escape");
  await drawer.waitFor({ state: "hidden" });
  assert.equal(
    await openMenu.evaluate((element) => element === document.activeElement),
    true,
    "closing drawer restores focus",
  );

  for (const view of [
    "Overview",
    "Review inbox",
    "Timeline",
    "Follow-ups",
    "Privacy",
  ]) {
    await openMenu.click();
    await nav(view);
    await page
      .getByRole("heading", {
        name: view === "Overview" ? /Less chasing/ : view,
        exact: view !== "Overview",
      })
      .waitFor();
    assert.equal(
      await page
        .locator("body")
        .evaluate((element) => element.scrollWidth <= window.innerWidth),
      true,
      `${view} fits mobile width`,
    );
  }
  const light = await page
    .locator("body")
    .evaluate((element) => getComputedStyle(element).backgroundColor);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.waitForTimeout(250);
  const dark = await page
    .locator("body")
    .evaluate((element) => getComputedStyle(element).backgroundColor);
  assert.notEqual(dark, light, "system dark mode changes the canvas");
  assert.deepEqual(errors, [], "browser has no uncaught application errors");
  console.log(
    "UI journey passed: real local import, evidence, edit validation, approval, draft copy/download, timeline, CSV, completion, source deletion, help, mobile focus/navigation and dark mode.",
  );
} finally {
  if (sourceId) await context.request.delete(`${API}/sources/${sourceId}`);
  const sources = await context.request
    .get(`${API}/sources`)
    .then((response) => response.json())
    .catch(() => []);
  for (const source of sources.filter((source) => source.name === name))
    await context.request.delete(`${API}/sources/${source.id}`);
  await context.close();
  await browser.close();
}
