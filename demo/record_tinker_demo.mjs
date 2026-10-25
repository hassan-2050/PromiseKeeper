// Capture actual completed Tinker results and a live consented checkpoint import.
import assert from "node:assert/strict";
import { chromium } from "playwright";
import { execFileSync } from "node:child_process";
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { pathToFileURL } from "node:url";
import { parseArgs } from "node:util";

const { values } = parseArgs({ options: {
  "run-dir": { type: "string" }, "web-url": { type: "string", default: "http://localhost:3001" },
  "api-url": { type: "string", default: "http://localhost:9000/api" },
} });
assert.ok(values["run-dir"], "--run-dir is required");
const runDir = resolve(values["run-dir"]);
const state = JSON.parse(readFileSync(resolve(runDir, "run.json"), "utf8"));
assert.equal(state.status, "completed");
assert.equal(state.selection_scoring_version, 2);
const demo = JSON.parse(readFileSync(resolve(runDir, "demo.json"), "utf8"));
const comparison = JSON.parse(readFileSync(resolve(runDir, "comparison.json"), "utf8"));
const assets = resolve("demo/assets/tinker");
const screenshots = resolve(assets, "screenshots");
const videoDir = resolve(assets, "video");
mkdirSync(screenshots, { recursive: true });
mkdirSync(videoDir, { recursive: true });
const browser = await chromium.launch({ headless: true, channel: "chrome" });
const context = await browser.newContext({ viewport: { width: 1920, height: 1080 },
  recordVideo: { dir: videoDir, size: { width: 1920, height: 1080 } } });
const health = await context.request.get(`${values["api-url"]}/health`).then(r => r.json());
assert.equal(health.inference, "remote", "Demo requires the opt-in Tinker API instance");
assert.equal(health.model_available, true);
assert.equal(health.checkpoint, state.selected_checkpoint.sampler_path);
// Warm the SDK connection before opening the video page. All benchmark latency
// rows retain their original cold calls; this demonstration is not a speed test.
console.log("Warming the actual checkpoint connection with a separate synthetic probe...");
const frozenTrain = readFileSync(resolve(runDir, "train.jsonl"), "utf8").trim().split(/\r?\n/).map(line => JSON.parse(line));
const warmText = frozenTrain.find(item => item.gold.length === 0).text;
const warm = await context.request.post(`${values["api-url"]}/import`, { timeout: 300000,
  data: { name: "Synthetic recording warm-up", text: warmText, allow_remote_inference: true } });
assert.equal(warm.status(), 200);
const warmData = await warm.json();
await context.request.delete(`${values["api-url"]}/sources/${warmData.source_id}`);
const page = await context.newPage();
page.setDefaultTimeout(30000);
const errors = [];
page.on("pageerror", error => errors.push(error.message));
const scenes = [];
const start = performance.now();
function mark(name) {
  const at = (performance.now() - start) / 1000;
  if (scenes.length) scenes.at(-1).end = at;
  scenes.push({ name, start: scenes.length ? at : 0 });
}
async function capture(name, fullPage = true) { await page.screenshot({ path: resolve(screenshots, `${name}.png`), fullPage }); }

mark("comparison");
await page.goto(pathToFileURL(resolve(runDir, "comparison.html")).href);
await page.getByRole("heading", { name: "Pipeline results", exact: true }).evaluate(el => el.scrollIntoView({ block: "start" }));
await capture("measured-comparison", false);
await page.waitForTimeout(7000);
mark("baseline");
const exampleSection = await page.locator("#illustration").count() ? page.locator("#illustration") : page.locator("#fixed-demo");
await exampleSection.locator("details").nth(1).evaluate(el => { el.open = false; });
await exampleSection.getByRole("heading").evaluate(el => el.scrollIntoView({ block: "start" }));
await capture("baseline-soft-refusal", false);
await page.waitForTimeout(6000);
mark("finetuned");
await exampleSection.locator("details").nth(0).evaluate(el => { el.open = false; });
await exampleSection.locator("details").nth(1).evaluate(el => { el.open = true; });
await capture("finetuned-soft-refusal", false);
await page.waitForTimeout(6000);
mark("consent");
await page.goto(values["web-url"], { waitUntil: "networkidle", timeout: 60000 });
await page.locator(".sidebar-add").click();
await page.getByLabel(/^Source name/).fill("Tinker checkpoint demo (authored synthetic)");
await page.locator("#import-box").fill(demo.text);
const consent = page.getByRole("checkbox", { name: /I agree to send these notes/ });
const find = page.getByRole("button", { name: "Find the promises", exact: true });
assert.equal(await consent.isChecked(), false);
assert.equal(await find.isDisabled(), true);
await capture("cloud-import-consent");
await page.waitForTimeout(5000);
await consent.check();
mark("inference");
const imported = page.waitForResponse(r => r.url() === `${values["api-url"]}/import` && r.request().method() === "POST", { timeout: 300000 });
await find.click();
const response = await imported;
assert.equal(response.status(), 200, "Actual checkpoint import must succeed");
const data = await response.json();
assert.ok(data.count > 0);
for (const item of data.commitments) assert.ok(demo.text.includes(item.evidence));
await page.getByRole("heading", { name: "Review inbox", exact: true }).waitFor();
await page.waitForTimeout(1500);
mark("review");
await capture("checkpoint-evidence-review");
await page.waitForTimeout(3000);
const originalSuggestion = data.commitments.find(item => /access matrix/i.test(item.claim));
assert.ok(originalSuggestion);
const card = page.locator(`article[data-commitment-id="${originalSuggestion.id}"]`);
assert.equal(await card.count(), 1);
await card.getByRole("button", { name: "Edit", exact: true }).click();
await card.getByLabel("Commitment", { exact: true }).fill("Review the access matrix after security sign-off");
await card.getByLabel("Owner", { exact: true }).fill("Dario");
await card.getByLabel("Private note", { exact: true }).fill("Synthetic demo review: this obligation remains conditional on security sign-off.");
await page.waitForTimeout(1500);
await card.getByRole("button", { name: "Save edits", exact: true }).click();
await capture("reviewer-clarifies-action");
await page.waitForTimeout(4000);
mark("followup");
await card.getByRole("button", { name: /looks right/i }).click();
await page.getByRole("navigation", { name: "Workspace navigation", exact: true }).getByRole("button", { name: "Follow-ups", exact: true }).click();
await page.getByRole("button", { name: /prepare draft/i }).first().click();
await page.waitForTimeout(3000);
await capture("approved-followup-draft");
await page.waitForTimeout(4000);
mark("privacy");
await page.getByRole("navigation", { name: "Workspace navigation", exact: true }).getByRole("button", { name: "Privacy", exact: true }).click();
await page.getByRole("heading", { name: "Tinker cloud model", exact: true }).waitFor();
await capture("cloud-privacy-boundary");
await page.waitForTimeout(5000);
scenes.at(-1).end = (performance.now() - start) / 1000;
assert.deepEqual(errors, []);
const video = page.video();
assert.ok(video);
await context.close();
await browser.close();
const recorded = await video.path();
execFileSync("ffmpeg", ["-y", "-v", "error", "-i", recorded, "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart", resolve(videoDir, "demo_silent.mp4")]);
const duration = Number(execFileSync("ffprobe", ["-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", resolve(videoDir, "demo_silent.mp4")], { encoding: "utf8" }).trim());
scenes.at(-1).end = duration;
writeFileSync(resolve(videoDir, "scene_timing.json"), JSON.stringify({ synthetic: true, duration, scenes }, null, 2) + "\n");
writeFileSync(resolve(assets, "capture_provenance.json"), JSON.stringify({ captured_at: new Date().toISOString(),
  checkpoint: health.checkpoint, run_dir: values["run-dir"], source_id: data.source_id, synthetic: true,
  actual_remote_inference: true, ui_extraction_replayed: false, comparison_outputs: "Preserved actual API responses", screenshot_capture: "Playwright Chrome screenshots of actual report and live app",
  sampler_pre_warmed: true, speed_claim: "None; benchmark latency retains cold calls separately",
  simulated_reviewer_edits: { original_claim: originalSuggestion?.claim, original_owner: originalSuggestion?.owner,
    approved_claim: "Review the access matrix after security sign-off", approved_owner: "Dario", reason: "Keep the condition visible before approval." },
  test_sha256: comparison.test_sha256, duration, scenes }, null, 2) + "\n");
console.log(`Captured actual Tinker comparison and review journey: ${duration.toFixed(2)} seconds.`);
