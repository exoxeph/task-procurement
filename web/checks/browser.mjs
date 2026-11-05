import { chromium } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";
import assert from "node:assert/strict";
import { mkdir, readFile, writeFile } from "node:fs/promises";

await mkdir("design/production", { recursive: true });
const data = JSON.parse(await readFile("public/data/results.json", "utf8"));
const browser = await chromium.launch({ channel: "msedge" });
const evidence = [];
try {
  const mockContext = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    colorScheme: "dark",
    reducedMotion: "reduce",
  });
  const page = await mockContext.newPage();
  const errors = [];
  const outbound = [];
  page.on("pageerror", (error) => errors.push(error.message));
  page.on("request", (request) => {
    if (!request.url().startsWith("http://127.0.0.1:3000"))
      outbound.push(request.url());
  });
  await page.goto("http://127.0.0.1:3000", { waitUntil: "networkidle" });
  assert.equal(await page.locator(".matrix tbody tr").count(), 10);
  assert.equal(await page.locator(".matrix .mismatch").count(), 13);
  assert.equal(
    await page.evaluate(
      () => document.documentElement.scrollWidth > innerWidth,
    ),
    false,
  );
  await page.screenshot({
    path: "design/production/review-room-desktop.png",
    fullPage: true,
  });
  await page.screenshot({ path: "design/production/review-room-hero.png" });

  for (const theme of ["dark", "light"]) {
    await page.evaluate(
      (theme) => (document.documentElement.dataset.theme = theme),
      theme,
    );
    const accessibility = await new AxeBuilder({ page })
      .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
      .analyze();
    evidence.push({
      check: `axe ${theme}`,
      violations: accessibility.violations,
    });
    assert.equal(
      accessibility.violations.length,
      0,
      JSON.stringify(
        accessibility.violations.map((v) => ({
          id: v.id,
          nodes: v.nodes.map((n) => n.target),
        })),
      ),
    );
  }
  await page.locator(".matrix .pack-button").nth(2).focus();
  await page.keyboard.press("Enter");
  await page.getByRole("dialog").waitFor();
  assert.ok(
    await page
      .getByRole("dialog")
      .innerText()
      .then((t) => t.includes("229.00")),
  );
  assert.ok(
    await page
      .locator("dialog")
      .evaluate((el) => el.contains(document.activeElement)),
  );
  await page.keyboard.press("Escape");
  assert.equal(await page.getByRole("dialog").count(), 0);
  await page
    .getByRole("button", { name: "Run mock check", exact: false })
    .click();
  await page
    .getByRole("status")
    .filter({ hasText: "Mock check complete" })
    .waitFor();
  assert.ok(
    await page
      .locator(".run-output")
      .innerText()
      .then((t) => t.includes("Reject")),
  );
  await page.locator("#run .source-details summary").click();
  assert.ok((await page.locator("#run .source-details mark").count()) > 0);
  await page
    .getByRole("button", { name: "Run mock check", exact: false })
    .click();
  await page.getByRole("button", { name: "Cancel check" }).click();
  await page.waitForTimeout(2600);
  assert.equal(await page.locator(".run-output .report").count(), 0);
  await page.route("**/api/run", (route) => route.abort());
  await page
    .getByRole("button", { name: "Run mock check", exact: false })
    .click();
  await page.locator(".error-box").waitFor();
  await page.getByRole("button", { name: "Replay saved answer" }).click();
  await page
    .getByRole("status")
    .filter({ hasText: "Saved answer ready" })
    .waitFor();
  assert.equal(await page.locator(".error-box").count(), 0);
  assert.deepEqual(errors, []);
  assert.deepEqual(outbound, []);
  evidence.push({
    check:
      "desktop, matrix, keyboard, quote highlighting, mock streaming, cancellation, offline replay",
    passed: true,
  });
  await page.close();
  await mockContext.close();

  // HTTPS test origin is fully intercepted and served from the local production
  // app. No DNS or external request is made, and the key is a dummy test value.
  const context = await browser.newContext({
    viewport: { width: 1440, height: 1000 },
    colorScheme: "dark",
    reducedMotion: "reduce",
  });
  const live = await context.newPage();
  const key = "dummy-private-test-key";
  const captured = [];
  let failure = null;
  await context.route("https://review.test/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname === "/api/samples") {
      await route.fulfill({
        json: data.packs.map(({ id, label, expected, text }) => ({
          id,
          label,
          expected,
          text,
        })),
      });
    } else if (url.pathname === "/api/run") {
      captured.push({
        url: request.url(),
        headers: request.headers(),
        body: request.postData(),
      });
      if (failure) await route.fulfill({ status: failure, body: key });
      else
        await route.fulfill({
          contentType: "application/x-ndjson",
          body:
            JSON.stringify({
              event: "result",
              ...data.packs[2].results.approach4,
              recorded: false,
            }) + "\n",
        });
    } else {
      const response = await context.request.get(
        `http://127.0.0.1:3001${url.pathname}${url.search}`,
      );
      await route.fulfill({ response });
    }
  });
  await live.goto("https://review.test", { waitUntil: "networkidle" });
  const run = live.getByRole("button", {
    name: "Run document check",
    exact: false,
  });
  assert.ok(await run.isDisabled());
  await live.getByLabel("OpenRouter API key", { exact: true }).fill(key);
  await live.getByRole("button", { name: "Show key", exact: true }).click();
  assert.equal(await live.locator("#api-key").getAttribute("type"), "text");
  await live.getByRole("button", { name: "Hide key", exact: true }).click();
  await run.click();
  await live
    .getByRole("status")
    .filter({ hasText: "Check complete" })
    .waitFor();
  assert.equal(captured.at(-1).headers["x-openrouter-key"], key);
  assert.ok(!captured.at(-1).url.includes(key));
  assert.ok(!captured.at(-1).body.includes(key));
  assert.deepEqual(
    await live.evaluate(() => ({
      local: { ...localStorage },
      session: { ...sessionStorage },
      cookie: document.cookie,
    })),
    { local: {}, session: {}, cookie: "" },
  );
  await live.getByRole("button", { name: "Forget key", exact: true }).click();
  assert.equal(await live.locator("#api-key").inputValue(), "");
  await live.getByLabel("OpenRouter API key", { exact: true }).fill(key);
  for (const code of [401, 402, 429, 500, 504]) {
    failure = code;
    await run.click();
    await live.locator(".error-box").waitFor();
    assert.ok(!(await live.locator(".error-box").innerText()).includes(key));
    assert.equal(await live.locator(".run-output .report").count(), 0);
  }
  failure = null;
  await live.getByLabel("Approach", { exact: true }).selectOption("approach1");
  await run.click();
  await live
    .getByRole("status")
    .filter({ hasText: "Check complete" })
    .waitFor();
  assert.equal(captured.at(-1).headers["x-openrouter-key"], undefined);
  await live.getByLabel("Approach", { exact: true }).selectOption("approach4");
  await live.reload({ waitUntil: "networkidle" });
  assert.equal(await live.locator("#api-key").inputValue(), "");
  evidence.push({
    check:
      "live HTTPS header only, baseline omission, memory only, forget/reload, mapped 401/402/429/500/504",
    passed: true,
  });
  await context.close();
  await writeFile(
    "design/production/browser-verification.json",
    JSON.stringify(evidence, null, 2),
  );
  console.info(
    "Browser acceptance passed: desktop, themes, keyboard, replay, streaming, cancellation, key privacy and mapped errors.",
  );
} finally {
  await browser.close();
}
