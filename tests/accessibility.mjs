import assert from "node:assert/strict";
import { writeFile } from "node:fs/promises";
import { chromium } from "playwright";
import axe from "axe-core";

const browser = await chromium.launch({ headless: true, channel: "chrome" });
const summary = [];
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
  });
  await page.goto(process.env.TEST_WEB_URL || "http://localhost:3001", {
    waitUntil: "networkidle",
  });
  await page.locator(".loading-state").waitFor({ state: "hidden" });
  await page.addScriptTag({ content: axe.source });
  const audit = async (theme, view) => {
    await page.waitForTimeout(250);
    const result = await page.evaluate(async () =>
      window.axe.run(document, {
        runOnly: { type: "tag", values: ["wcag2a", "wcag2aa", "wcag21aa"] },
      }),
    );
    summary.push({
      theme,
      view,
      violations: result.violations.length,
      passed_rules: result.passes.length,
      incomplete_rules: result.incomplete.map((rule) => rule.id),
    });
    for (const violation of result.violations)
      console.error(
        JSON.stringify({
          theme,
          view,
          id: violation.id,
          nodes: violation.nodes.map((node) => ({
            target: node.target,
            detail: node.failureSummary,
          })),
        }),
      );
  };
  for (const theme of ["light", "dark"]) {
    await page.setViewportSize({ width: 1440, height: 1000 });
    await page.emulateMedia({ colorScheme: theme });
    for (const view of [
      "Overview",
      "Review inbox",
      "Import notes",
      "Timeline",
      "Follow-ups",
      "Privacy",
    ]) {
      if (view === "Import notes") await page.locator(".sidebar-add").click();
      else
        await page
          .getByRole("navigation", {
            name: "Workspace navigation",
            exact: true,
          })
          .getByRole("button", { name: view, exact: true })
          .click();
      if (view === "Review inbox")
        await page.getByLabel("Status", { exact: true }).selectOption("all");
      await audit(theme, view);
    }
    await page.getByRole("button", { name: "Help", exact: true }).click();
    await audit(theme, "Help dialog");
    await page.keyboard.press("Escape");
    await page.setViewportSize({ width: 390, height: 844 });
    await page
      .getByRole("button", { name: "Open navigation", exact: true })
      .click();
    await audit(theme, "Mobile navigation");
    await page.keyboard.press("Escape");
  }
  const report = {
    tool: `axe-core ${axe.version}`,
    scope:
      "Automated WCAG 2 A/AA and 2.1 AA rules on the listed UI states; not a complete manual accessibility audit.",
    checked_at: new Date().toISOString(),
    states: summary,
  };
  await writeFile(
    "docs/ui_accessibility.json",
    JSON.stringify(report, null, 2) + "\n",
  );
  assert.ok(
    summary.every((state) => state.violations === 0),
    "resolve the reported accessibility violations",
  );
  console.log(
    `Accessibility checks passed for ${summary.length} light/dark page, dialog and mobile navigation states.`,
  );
} finally {
  await browser.close();
}
