// Real production rewrite check. Only Approach 1 is posted; no API key or paid AI call.
import { chromium } from "@playwright/test";
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";

const origin = "http://127.0.0.1:3001";
const routes = JSON.parse(await readFile(".next/routes-manifest.json", "utf8"));
const rewrite = routes.rewrites.afterFiles.find(
  (route) => route.source === "/api/:path*",
);
assert.equal(
  rewrite?.destination,
  "https://task-procurement.vercel.app/api/:path*",
);
const browser = await chromium.launch({ channel: "msedge" });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 1000 },
    reducedMotion: "reduce",
  });
  const errors = [];
  const posts = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (new URL(request.url()).pathname === "/api/run") {
      assert.equal(request.method(), "POST");
      assert.equal(request.headers()["x-openrouter-key"], undefined);
      assert.equal(JSON.parse(request.postData()).approach, "approach1");
      posts.push(request.url());
    }
  });
  const samplesReady = page.waitForResponse(`${origin}/api/samples`);
  const document = await page.goto(origin, { waitUntil: "networkidle" });
  assert.equal(document.status(), 200);
  const samplesResponse = await samplesReady;
  const samplesLoaded = samplesResponse.ok();
  const samples = samplesLoaded ? await samplesResponse.json() : [];
  if (samplesLoaded) {
    assert.equal(samples.length, 10);
    assert.ok(samples.every((sample) => sample.text && sample.expected));
    assert.equal(await page.locator(".service-notice").count(), 0);
  } else {
    await page.locator(".service-notice").waitFor();
  }
  assert.equal(await page.locator("#sample option").count(), 10);
  assert.ok(await page.locator("#api-key").isDisabled());
  await page
    .getByRole("button", { name: "Run mock check", exact: false })
    .click();
  await page
    .getByRole("status")
    .filter({ hasText: "Saved answer ready" })
    .waitFor();
  assert.equal(posts.length, 0);
  assert.equal(await page.locator(".run-output .report").count(), 1);

  await page
    .getByRole("button", { name: "Live (your key)", exact: true })
    .click();
  await page.getByLabel("Approach", { exact: true }).selectOption("approach1");
  const runResponse = page.waitForResponse(`${origin}/api/run`);
  await page
    .getByRole("button", { name: "Run document check", exact: false })
    .click();
  const response = await runResponse;
  const body = await response.body();
  await page.waitForFunction(
    () => {
      const status = document.querySelector(".run-status")?.textContent;
      return status === "Check complete" || status === "Check did not complete";
    },
    undefined,
    { timeout: 30_000 },
  );
  assert.equal(posts.length, 1);
  assert.equal(await page.locator("#run [aria-busy=true]").count(), 0);
  const error = page.locator(".error-box");
  const message = (await error.count()) ? await error.innerText() : null;
  if (message) assert.match(message, /replay|again/i);
  else assert.equal(await page.locator(".run-output .report").count(), 1);
  assert.deepEqual(errors, []);

  const evidence = {
    checkedAt: new Date().toISOString(),
    backend: "https://task-procurement.vercel.app",
    apiRewrite: rewrite.destination,
    pageStatus: document.status(),
    samplesStatus: samplesResponse.status(),
    samplesLoaded: samples.length,
    savedSamplesFallback: !samplesLoaded,
    mockPosts: 0,
    baselinePosts: posts.length,
    baselineStatus: response.status(),
    baselineResponseBytes: body.length,
    outcome: message ? "friendly error" : "completed result",
    displayedMessage: message,
    paidModelCalls: 0,
  };
  await mkdir("design/production", { recursive: true });
  await writeFile(
    "design/production/live-backend-verification.json",
    JSON.stringify(evidence, null, 2),
  );
  console.info(JSON.stringify(evidence, null, 2));
} finally {
  await browser.close();
}
