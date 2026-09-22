#!/usr/bin/env node
/**
 * probes/locator_probe.mjs — A/B verification of the Passage Locator (I-103).
 *
 * Why this exists and why it is not a unit test: the Stage-1 diagnosis
 * (RECIPROCAL_PASSAGE_STAGE1_INSTRUMENT_DIAGNOSIS_2026-09-22.md) had to
 * reproduce well.js scoring offline to explain a NO_SOURCES, and said plainly
 * that this is a reproduction, not the engine. A locator that changes query
 * routing has to be proved against the shipped bytes in a real browser, or the
 * proof is about a copy.
 *
 * So this borrows freeze_probes.mjs's technique wholesale -- real static
 * server, real headless Chrome over raw CDP, real #ask-form submit, output read
 * back out of the real DOM -- and adds the one thing a freeze cannot do: it
 * runs every question TWICE against the SAME live corpus, once on origin/main's
 * well.js and once on the candidate. A regression then has nowhere to hide in a
 * corpus-version difference, because both sides read the same corpus bytes.
 *
 * The load-bearing assertion is the boring one: on all ten frozen probe
 * questions, candidate output must equal baseline output exactly -- same
 * outcome, same passage ids. That is what "the abstention thresholds were not
 * weakened" means when it is measured instead of asserted.
 *
 * Deliberately NOT done here: writing probes/receipt-korpus-0.3.json. That file
 * is frozen evidence of an earlier korpus under an earlier engine; this run
 * writes its own receipt and leaves that one alone.
 *
 * Requires Node >=22 (built-in fetch + WebSocket) and an installed Chrome/Edge.
 * No npm packages, no network beyond 127.0.0.1, no generative calls.
 */

import { spawn, execFileSync } from "node:child_process";
import { readFile, writeFile, mkdtemp, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITE_DIR = path.resolve(HERE, "..");
const RECEIPT_PATH = path.join(HERE, "receipt-locator.json");
const BASELINE_REF = process.env.LOCATOR_BASELINE_REF || "origin/main";

const RAF_PATCH_NOTE =
  "requestAnimationFrame patched to fire via setTimeout(0) for this run only, " +
  "inside the throwaway CDP page context -- well.js uses rAF purely to yield " +
  "one paint frame before search()/runLocator(); it is scheduling, not scoring. " +
  "Applied identically to baseline and candidate.";

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
};

const log = (...a) => console.error("[locator_probe]", ...a);

/* ---------- static server, with per-path byte overrides for the baseline ----------
   Both variants serve the SAME directory, so corpus.json, spine.jsonl and
   styles are byte-identical on both sides by construction. Only the files the
   candidate actually changed are swapped, and only for the baseline. */
function startStaticServer(rootDir, overrides = {}) {
  return new Promise((resolve, reject) => {
    const server = createServer(async (req, res) => {
      try {
        if (req.method !== "GET" && req.method !== "HEAD") return void res.writeHead(405).end();
        const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
        const rel = urlPath === "/" ? "/index.html" : urlPath;
        let buf;
        if (Object.prototype.hasOwnProperty.call(overrides, rel)) {
          if (overrides[rel] === null) return void res.writeHead(404).end("not found (baseline)");
          buf = Buffer.from(overrides[rel], "utf8");
        } else {
          const abs = path.normalize(path.join(rootDir, rel));
          if (!abs.startsWith(path.normalize(rootDir))) return void res.writeHead(403).end();
          buf = await readFile(abs);
        }
        res.writeHead(200, {
          "content-type": CONTENT_TYPES[path.extname(rel).toLowerCase()] || "application/octet-stream",
          "content-length": buf.length,
        });
        req.method === "HEAD" ? res.end() : res.end(buf);
      } catch (err) {
        res.writeHead(404).end("not found: " + String(err && err.message));
      }
    });
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/chromium",
].filter(Boolean);

async function findChrome() {
  const { access } = await import("node:fs/promises");
  for (const c of CHROME_CANDIDATES) {
    try { await access(c); return c; } catch { /* next */ }
  }
  throw new Error("No Chrome/Chromium/Edge found. Set CHROME_PATH.");
}

async function waitForCdp(port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastErr;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (r.ok) return await r.json();
    } catch (e) { lastErr = e; }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error("CDP never came up on " + port + ": " + lastErr);
}

async function openTab(port) {
  let resp;
  try {
    resp = await fetch(`http://127.0.0.1:${port}/json/new`, { method: "PUT" });
    if (!resp.ok) throw new Error("PUT -> " + resp.status);
  } catch {
    resp = await fetch(`http://127.0.0.1:${port}/json/new`, { method: "GET" });
  }
  return resp.json();
}

function connectCdp(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map();
    ws.addEventListener("open", () => resolve(client));
    ws.addEventListener("error", (e) => reject(new Error("CDP ws error: " + e.message)));
    ws.addEventListener("message", (ev) => {
      let msg; try { msg = JSON.parse(ev.data); } catch { return; }
      if (msg.id && pending.has(msg.id)) {
        const { resolve: res, reject: rej } = pending.get(msg.id);
        pending.delete(msg.id);
        msg.error ? rej(new Error("CDP " + msg.error.message)) : res(msg.result);
      }
    });
    const client = {
      send: (method, params = {}) => new Promise((res, rej) => {
        const id = nextId++;
        pending.set(id, { resolve: res, reject: rej });
        ws.send(JSON.stringify({ id, method, params }));
      }),
      close() { try { ws.close(); } catch { /* ignore */ } },
    };
  });
}

async function evaluate(cdp, expression) {
  const r = await cdp.send("Runtime.evaluate", { expression, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error("page-side exception: " + JSON.stringify(r.exceptionDetails.exception));
  return r.result && r.result.value;
}

/* ---------- in-page harness: DOM plumbing only, zero scoring logic ---------- */
function askExpression(question) {
  const q = JSON.stringify(question);
  return `(async function (question) {
    var srcBody = document.getElementById('rw-src-body');
    var engBody = document.getElementById('rw-eng-body');
    var input = document.getElementById('ask-input');
    var form = document.getElementById('ask-form');
    srcBody.textContent = '';
    input.value = question;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    var deadline = Date.now() + 8000;
    function settled() {
      return !!(srcBody.querySelector('.to-abstain') || srcBody.querySelector('.to-src'));
    }
    while (Date.now() < deadline && !settled()) {
      await new Promise(function (r) { setTimeout(r, 50); });
    }
    var abstainEl = srcBody.querySelector('.to-abstain .ab-type');
    var receiptEl = engBody.querySelector('.to-rcpt');
    return {
      abstainType: abstainEl ? abstainEl.textContent.trim().replace(/[\\[\\]]/g, '') : null,
      abstainMsg: srcBody.querySelector('.to-abstain') ? srcBody.querySelector('.to-abstain').textContent : null,
      receiptLine: receiptEl ? receiptEl.textContent : null,
      notes: Array.prototype.map.call(srcBody.querySelectorAll('.to-a'), function (n) { return n.textContent; }),
      metas: Array.prototype.map.call(srcBody.querySelectorAll('.src-m'), function (n) { return n.textContent; }),
      hasLocator: typeof window.GenesisLocator !== 'undefined',
      timedOut: !settled()
    };
  })(${q})`;
}

function outcomeOf(r) {
  if (r.abstainType) return { outcome: r.abstainType, passageIds: null };
  if (r.receiptLine) {
    if (/no passage matched solidly/.test(r.receiptLine)) return { outcome: "NO_SOURCES", passageIds: null };
    const m = r.receiptLine.match(/passages:\s*(.+?)\s*\u00b7\s*korpus/);
    if (m) return { outcome: "ANSWERED", passageIds: m[1].split("\u00b7").map((s) => s.trim().split("@")[0]) };
  }
  if (r.timedOut) return { outcome: "TIMEOUT_NO_RESULT", passageIds: null };
  return { outcome: "UNKNOWN", passageIds: null };
}

const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

async function killChrome(proc) {
  if (!proc || proc.killed) return;
  try {
    if (process.platform === "win32" && proc.pid) {
      execFileSync("taskkill", ["/PID", String(proc.pid), "/T", "/F"], { stdio: "ignore" });
    } else proc.kill("SIGKILL");
  } catch { /* best effort */ }
}

/* ---------- what we ask ----------
   Group A is the regression half: the ten questions frozen in korpus-0.3.json.
   Their expectation is not a hardcoded outcome -- it is "whatever the baseline
   engine does on this same corpus". Group B is the locator half. */
const LOCATOR_CASES = [
  { id: "stage1-verbatim", mustDiffer: true, expect: "ANSWERED",
    expectIds: ["kjv:genesis-1", "kjv:genesis-2", "kjv:genesis-3"],
    q: "What structural patterns of naming, separation, patience, and discovered value appear in " +
       "Genesis 1\u20133, without turning them into moral ranking or authority over people or agents?" },
  { id: "chapter", mustDiffer: true, expect: "ANSWERED", expectIds: ["kjv:genesis-1"], q: "Genesis 1" },
  { id: "range-endash", mustDiffer: true, expect: "ANSWERED",
    expectIds: ["kjv:genesis-1", "kjv:genesis-2", "kjv:genesis-3"], q: "Genesis 1\u20133" },
  { id: "whole-number", mustDiffer: true, expect: "ANSWERED",
    expectIds: ["tao:tao-te-ching-72"], q: "Tao Te Ching 72" },
  { id: "lens-alongside-address", mustDiffer: true, expect: "ANSWERED",
    expectIds: ["kjv:genesis-1"], q: "what does Genesis 1 say about light?",
    // The address quoted back must be the address, and the unanswered half must
    // be the subject -- not the request scaffolding around it. Both were real
    // defects caught by the first run of this probe.
    expectNote: /addressed as “genesis 1”/ },
  { id: "lens-names-only-the-subject", mustDiffer: true, expect: "ANSWERED",
    expectIds: ["kjv:genesis-1"], q: "what does Genesis 1 say about light?",
    expectNote: /you also asked about: light — that part is not answered here/ },
  { id: "not-in-corpus", mustDiffer: true, expect: "LOCATOR_NOT_IN_CORPUS", q: "Genesis 99" },
  { id: "ambiguous-work", mustDiffer: true, expect: "LOCATOR_AMBIGUOUS", q: "upanishad 1.1" },
  { id: "too-broad", mustDiffer: true, expect: "LOCATOR_TOO_BROAD", q: "Bhagavad Gita 2" },
];

async function main() {
  const corpus = JSON.parse(await readFile(path.join(SITE_DIR, "corpus.json"), "utf8"));
  const frozen = JSON.parse(await readFile(path.join(HERE, "korpus-0.3.json"), "utf8"));
  log("live corpus:", corpus.version, corpus.manifestSha256.slice(0, 12), corpus.passageCount, "passages");

  const git = (ref, file) =>
    execFileSync("git", ["show", `${ref}:${file}`], { cwd: SITE_DIR, encoding: "utf8" });
  const baselineOverrides = {
    "/well.js": git(BASELINE_REF, "well.js"),
    "/index.html": git(BASELINE_REF, "index.html"),
    "/locator.js": null, // baseline must not have it, even by accident
  };
  log("baseline bytes taken from", BASELINE_REF);

  const candidateSrv = await startStaticServer(SITE_DIR);
  const baselineSrv = await startStaticServer(SITE_DIR, baselineOverrides);
  const urlOf = (s) => `http://127.0.0.1:${s.address().port}/index.html`;

  const chromePath = await findChrome();
  const cdpPort = 9400 + Math.floor(Math.random() * 400);
  const userDataDir = await mkdtemp(path.join(tmpdir(), "locator-probe-"));
  const chromeProc = spawn(chromePath, [
    "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
    "--no-default-browser-check", "--disable-extensions",
    `--remote-debugging-port=${cdpPort}`, `--user-data-dir=${userDataDir}`, "about:blank",
  ], { stdio: "ignore" });

  let receipt;
  try {
    await waitForCdp(cdpPort, 20000);

    async function openVariant(url) {
      const tab = await openTab(cdpPort);
      const cdp = await connectCdp(tab.webSocketDebuggerUrl);
      await cdp.send("Page.enable");
      await cdp.send("Runtime.enable");
      await cdp.send("Page.navigate", { url });
      await new Promise((r) => setTimeout(r, 1500));
      await evaluate(cdp, "(function(){ window.requestAnimationFrame = function(cb){ " +
        "return setTimeout(function(){ cb(performance.now()); }, 0); }; return true; })()");
      return cdp;
    }

    const candidate = await openVariant(urlOf(candidateSrv));
    const baseline = await openVariant(urlOf(baselineSrv));

    const wiring = {
      candidateHasLocator: await evaluate(candidate, "typeof window.GenesisLocator !== 'undefined'"),
      baselineHasLocator: await evaluate(baseline, "typeof window.GenesisLocator !== 'undefined'"),
    };
    log("wiring:", JSON.stringify(wiring));

    const regression = [];
    for (const p of frozen.probes) {
      const c = outcomeOf(await evaluate(candidate, askExpression(p.question)));
      const b = outcomeOf(await evaluate(baseline, askExpression(p.question)));
      const identical = c.outcome === b.outcome && same(c.passageIds, b.passageIds);
      regression.push({ probeId: p.probeId, question: p.question, frozenExpected: p.expectedOutcome,
        baseline: b, candidate: c, identical });
      log(identical ? "  = " : "  ! ", p.probeId, b.outcome, "->", c.outcome);
    }

    const locator = [];
    for (const t of LOCATOR_CASES) {
      const raw = await evaluate(candidate, askExpression(t.q));
      const c = outcomeOf(raw);
      const b = outcomeOf(await evaluate(baseline, askExpression(t.q)));
      const outcomeOk = c.outcome === t.expect;
      const idsOk = !t.expectIds || same([...(c.passageIds || [])].sort(), [...t.expectIds].sort());
      const noteOk = !t.expectNote || (raw.notes || []).some((n) => t.expectNote.test(n));
      const differs = !t.mustDiffer || c.outcome !== b.outcome || !same(c.passageIds, b.passageIds);
      locator.push({ id: t.id, question: t.q, expected: t.expect, expectedIds: t.expectIds || null,
        baseline: b, candidate: c, notes: raw.notes, outcomeOk, idsOk, noteOk,
        differsFromBaseline: differs, pass: outcomeOk && idsOk && noteOk && differs });
      log(locator[locator.length - 1].pass ? "  ok " : "  FAIL", t.id, b.outcome, "->", c.outcome);
    }

    const regressionsBroken = regression.filter((r) => !r.identical);
    const locatorFailed = locator.filter((l) => !l.pass);
    const pass = regressionsBroken.length === 0 && locatorFailed.length === 0 &&
      wiring.candidateHasLocator === true && wiring.baselineHasLocator === false;

    receipt = {
      generatedAt: new Date().toISOString(),
      object: "PASSAGE_LOCATOR (I-103)",
      baselineRef: BASELINE_REF,
      baselineHead: execFileSync("git", ["rev-parse", BASELINE_REF], { cwd: SITE_DIR, encoding: "utf8" }).trim(),
      candidateBranch: execFileSync("git", ["rev-parse", "--abbrev-ref", "HEAD"], { cwd: SITE_DIR, encoding: "utf8" }).trim(),
      corpus: { version: corpus.version, manifestSha256: corpus.manifestSha256, passageCount: corpus.passageCount },
      method: "two static servers over the SAME site directory (baseline swaps well.js/index.html for " +
        BASELINE_REF + " bytes and 404s locator.js); one headless Chrome, one tab each, raw CDP; real " +
        "#ask-form submit and real DOM read-back; no scoring logic reimplemented. " + RAF_PATCH_NOTE,
      chromeExecutable: chromePath,
      wiring,
      regression, locator,
      summary: {
        label: pass ? "PASS" : "FAIL",
        frozenProbesIdenticalToBaseline: `${regression.length - regressionsBroken.length}/${regression.length}`,
        locatorCasesPassed: `${locator.length - locatorFailed.length}/${locator.length}`,
        broken: regressionsBroken.map((r) => r.probeId),
        failed: locatorFailed.map((l) => l.id),
      },
    };

    candidate.close(); baseline.close();
  } finally {
    await killChrome(chromeProc);
    candidateSrv.close(); baselineSrv.close();
    await rm(userDataDir, { recursive: true, force: true }).catch(() => {});
  }

  await writeFile(RECEIPT_PATH, JSON.stringify(receipt, null, 2) + "\n", "utf8");
  log("wrote", RECEIPT_PATH, "->", receipt.summary.label);
  console.log(JSON.stringify(receipt.summary, null, 2));
  if (receipt.summary.label !== "PASS") process.exitCode = 1;
}

main().catch((err) => { log("FATAL:", err); process.exitCode = 1; });
