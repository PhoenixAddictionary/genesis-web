#!/usr/bin/env node
/**
 * probes/freeze_probes.mjs — korpus 0.3 retrieval-quality freeze step.
 *
 * What this deliberately does NOT do: reimplement well.js's tokenize()/search()
 * (BM25-ish, K1=1.5, B=0.75, light stemming). well.js is an IIFE with no
 * exports and DOM dependencies, so its scoring is not cleanly importable as a
 * pure function, and well.js itself is off-limits to edit in this maker
 * packet (another concurrent packet may be touching it). A second,
 * hand-written scoring implementation would silently diverge from the real
 * engine and make the receipt dishonest.
 *
 * What this does instead: serves the real, unmodified site locally, drives a
 * real headless Chrome against it over raw CDP (the same "installed Chrome
 * over raw CDP" technique this folder's own capture.py already uses for
 * verification — see RUN.md), fills the real #ask-input, dispatches a real
 * 'submit' on #ask-form, and reads the ACTUAL rendered output back out of the
 * DOM (#rw-src-body / #rw-eng-body) that well.js's own handler produced. So
 * every score, hit, and abstention type in the receipt is the shipped
 * engine's real output, not a guess.
 *
 * No network calls beyond 127.0.0.1, no generative/LLM calls. Requires only
 * Node >=22 (built-in fetch + WebSocket) and a local Chrome/Edge install —
 * zero npm packages.
 */

import { spawn, execFileSync } from "node:child_process";
import { readFile, writeFile, mkdtemp, rm } from "node:fs/promises";
import { createServer } from "node:http";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const SITE_DIR = path.resolve(HERE, ".."); // well-prototype-src/
const PROBES_PATH = path.join(HERE, "korpus-0.3.json");
const RECEIPT_PATH = path.join(HERE, "receipt-korpus-0.3.json");

const RAF_PATCH_NOTE =
  "requestAnimationFrame patched to fire via setTimeout(0) for this freeze " +
  "run only, inside the throwaway CDP page context. well.js uses rAF purely " +
  "to yield one paint frame before calling search() (see well.js comment " +
  "'yield one frame so reading N passages can paint; not inserted latency') " +
  "-- it is scheduling, not scoring. Headless/offscreen pages routinely " +
  "starve real rAF callbacks, so this keeps the freeze step deterministic " +
  "without touching tokenize()/search() at all.";

const CONTENT_TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".mjs": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
};

function log(...args) {
  console.error("[freeze_probes]", ...args);
}

// ---------- tiny static file server (GET-only, path-traversal guarded) ----------
function startStaticServer(rootDir) {
  return new Promise((resolve, reject) => {
    const server = createServer(async (req, res) => {
      try {
        if (req.method !== "GET" && req.method !== "HEAD") {
          res.writeHead(405).end("method not allowed");
          return;
        }
        const urlPath = decodeURIComponent((req.url || "/").split("?")[0]);
        const rel = urlPath === "/" ? "/index.html" : urlPath;
        const abs = path.normalize(path.join(rootDir, rel));
        if (!abs.startsWith(path.normalize(rootDir))) {
          res.writeHead(403).end("forbidden");
          return;
        }
        const buf = await readFile(abs);
        const ext = path.extname(abs).toLowerCase();
        res.writeHead(200, {
          "content-type": CONTENT_TYPES[ext] || "application/octet-stream",
          "content-length": buf.length,
        });
        if (req.method === "HEAD") res.end();
        else res.end(buf);
      } catch (err) {
        res.writeHead(404).end("not found: " + String(err && err.message));
      }
    });
    server.on("error", reject);
    server.listen(0, "127.0.0.1", () => resolve(server));
  });
}

// ---------- Chrome discovery + launch ----------
const CHROME_CANDIDATES = [
  process.env.CHROME_PATH,
  "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
  "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
  "C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
  "/usr/bin/google-chrome",
  "/usr/bin/google-chrome-stable",
  "/usr/bin/chromium-browser",
  "/usr/bin/chromium",
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
].filter(Boolean);

async function findChrome() {
  const { access } = await import("node:fs/promises");
  for (const candidate of CHROME_CANDIDATES) {
    try {
      await access(candidate);
      return candidate;
    } catch {
      /* try next */
    }
  }
  throw new Error(
    "No Chrome/Chromium/Edge executable found (checked: " +
      CHROME_CANDIDATES.join(", ") +
      "). Set CHROME_PATH to override."
  );
}

async function waitForCdp(port, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  let lastErr;
  while (Date.now() < deadline) {
    try {
      const r = await fetch(`http://127.0.0.1:${port}/json/version`);
      if (r.ok) return await r.json();
    } catch (err) {
      lastErr = err;
    }
    await new Promise((r) => setTimeout(r, 150));
  }
  throw new Error("CDP endpoint never came up on port " + port + ": " + lastErr);
}

async function openTab(port, targetUrl) {
  // PUT is the modern CDP HTTP endpoint verb for /json/new; fall back to GET
  // for older Chrome/Edge builds that still accept it.
  let resp;
  try {
    resp = await fetch(`http://127.0.0.1:${port}/json/new`, { method: "PUT" });
    if (!resp.ok) throw new Error("PUT /json/new -> " + resp.status);
  } catch {
    resp = await fetch(`http://127.0.0.1:${port}/json/new`, { method: "GET" });
  }
  const tab = await resp.json();
  return tab;
}

// ---------- minimal CDP client over the built-in WebSocket ----------
function connectCdp(wsUrl) {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(wsUrl);
    let nextId = 1;
    const pending = new Map();
    ws.addEventListener("open", () => resolve(client));
    ws.addEventListener("error", (e) => reject(new Error("CDP ws error: " + e.message)));
    ws.addEventListener("message", (ev) => {
      let msg;
      try {
        msg = JSON.parse(ev.data);
      } catch {
        return;
      }
      if (msg.id && pending.has(msg.id)) {
        const { resolve: res, reject: rej } = pending.get(msg.id);
        pending.delete(msg.id);
        if (msg.error) rej(new Error("CDP " + msg.error.message));
        else res(msg.result);
      }
    });
    const client = {
      send(method, params = {}) {
        const id = nextId++;
        return new Promise((res, rej) => {
          pending.set(id, { resolve: res, reject: rej });
          ws.send(JSON.stringify({ id, method, params }));
        });
      },
      close() {
        try {
          ws.close();
        } catch {
          /* ignore */
        }
      },
    };
  });
}

async function evaluate(cdp, expression) {
  const result = await cdp.send("Runtime.evaluate", {
    expression,
    awaitPromise: true,
    returnByValue: true,
  });
  if (result.exceptionDetails) {
    throw new Error(
      "page-side exception: " + JSON.stringify(result.exceptionDetails.exception)
    );
  }
  return result.result && result.result.value;
}

// ---------- the in-page probe harness (DOM plumbing only, zero scoring logic) ----------
function askExpression(question) {
  const q = JSON.stringify(question);
  return `(async function (question) {
    var srcBody = document.getElementById('rw-src-body');
    var engBody = document.getElementById('rw-eng-body');
    var input = document.getElementById('ask-input');
    var form = document.getElementById('ask-form');
    input.value = question;
    form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    var deadline = Date.now() + 5000;
    function settled() {
      return !!(srcBody.querySelector('.to-abstain') ||
                srcBody.querySelector('.to-src') ||
                engBody.querySelector('.to-rcpt'));
    }
    while (Date.now() < deadline && !settled()) {
      await new Promise(function (r) { setTimeout(r, 50); });
    }
    var abstainEl = srcBody.querySelector('.to-abstain .ab-type');
    var abstainMsgEl = srcBody.querySelector('.to-abstain');
    var receiptEl = engBody.querySelector('.to-rcpt');
    var sources = Array.prototype.map.call(srcBody.querySelectorAll('.to-src'), function (el) {
      return {
        excerpt: el.querySelector('.src-x') ? el.querySelector('.src-x').textContent : null,
        meta: el.querySelector('.src-m') ? el.querySelector('.src-m').textContent : null
      };
    });
    return {
      question: question,
      abstainType: abstainEl ? abstainEl.textContent.trim() : null,
      abstainMsg: abstainMsgEl ? abstainMsgEl.textContent : null,
      receiptLine: receiptEl ? receiptEl.textContent : null,
      sources: sources,
      timedOut: !settled()
    };
  })(${q})`;
}

function parseActual(result) {
  if (result.timedOut && !result.abstainType && !result.receiptLine) {
    return { outcome: "TIMEOUT_NO_RESULT", passageIds: null };
  }
  if (result.abstainType) {
    return { outcome: result.abstainType.replace(/[[\]]/g, "").trim(), passageIds: null };
  }
  if (result.receiptLine) {
    if (/no passage matched solidly/.test(result.receiptLine)) {
      return { outcome: "NO_SOURCES", passageIds: null };
    }
    const m = result.receiptLine.match(/passages:\s*(.+?)\s*\u00b7\s*korpus/);
    if (m) {
      const ids = m[1].split("\u00b7").map((s) => s.trim().split("@")[0]);
      return { outcome: "ANSWERED", passageIds: ids };
    }
  }
  return { outcome: "UNKNOWN", passageIds: null };
}

function sameSet(a, b) {
  if (!a || !b) return false;
  if (a.length !== b.length) return false;
  const sa = [...a].sort();
  const sb = [...b].sort();
  return sa.every((v, i) => v === sb[i]);
}

async function killChrome(proc) {
  if (!proc || proc.killed) return;
  try {
    if (process.platform === "win32" && proc.pid) {
      execFileSync("taskkill", ["/PID", String(proc.pid), "/T", "/F"], { stdio: "ignore" });
    } else {
      proc.kill("SIGKILL");
    }
  } catch {
    /* best-effort */
  }
}

async function main() {
  const probesRaw = await readFile(PROBES_PATH, "utf8");
  const probeSet = JSON.parse(probesRaw);

  const corpusRaw = await readFile(path.join(SITE_DIR, "corpus.json"), "utf8");
  const corpus = JSON.parse(corpusRaw);
  log("corpus.json read directly from disk: version", corpus.version, "manifestSha256", corpus.manifestSha256);

  if (corpus.manifestSha256 !== probeSet.manifestSha256) {
    throw new Error(
      "manifestSha256 mismatch: probes/korpus-0.3.json says " +
        probeSet.manifestSha256 +
        " but the live corpus.json on disk says " +
        corpus.manifestSha256 +
        " -- korpus 0.3 must be frozen; refusing to write a receipt against a moved target."
    );
  }

  const server = await startStaticServer(SITE_DIR);
  const httpPort = server.address().port;
  log("static server up on 127.0.0.1:" + httpPort, "serving", SITE_DIR);

  const chromePath = await findChrome();
  log("chrome executable:", chromePath);

  const userDataDir = await mkdtemp(path.join(tmpdir(), "well-freeze-cdp-"));
  const cdpPort = 9000 + Math.floor(Math.random() * 900); // avoid clashing with a dev session on 9222
  const chromeArgs = [
    "--headless=new",
    "--disable-gpu",
    "--hide-scrollbars",
    "--no-first-run",
    "--no-default-browser-check",
    "--window-size=1280,900",
    `--remote-debugging-port=${cdpPort}`,
    `--user-data-dir=${userDataDir}`,
    "about:blank",
  ];
  const chromeProc = spawn(chromePath, chromeArgs, { stdio: "ignore" });

  let cdp;
  let receipt;
  try {
    await waitForCdp(cdpPort, 10000);
    const tab = await openTab(cdpPort, "about:blank");
    if (!tab.webSocketDebuggerUrl) {
      throw new Error("no webSocketDebuggerUrl in /json/new response: " + JSON.stringify(tab));
    }
    cdp = await connectCdp(tab.webSocketDebuggerUrl);
    await cdp.send("Page.enable");
    await cdp.send("Runtime.enable");

    const targetUrl = `http://127.0.0.1:${httpPort}/index.html`;
    await cdp.send("Page.navigate", { url: targetUrl });

    // poll for real page readiness instead of trusting a fixed sleep
    const readyDeadline = Date.now() + 10000;
    let ready = false;
    while (Date.now() < readyDeadline) {
      const state = await evaluate(cdp, "document.readyState");
      if (state === "complete" && (await evaluate(cdp, "!!document.getElementById('ask-form')"))) {
        ready = true;
        break;
      }
      await new Promise((r) => setTimeout(r, 100));
    }
    if (!ready) throw new Error("page never reached a ready state with #ask-form present");

    await evaluate(
      cdp,
      "(function(){ window.requestAnimationFrame = function(cb){ return setTimeout(function(){ cb(performance.now()); }, 0); }; return true; })()"
    );
    log("page loaded:", targetUrl, "|", RAF_PATCH_NOTE);

    const perProbe = [];
    for (const probe of probeSet.probes) {
      const raw = await evaluate(cdp, askExpression(probe.question));
      const actual = parseActual(raw);
      let match;
      if (probe.expectedOutcome === "ANSWERED") {
        match = actual.outcome === "ANSWERED" && sameSet(actual.passageIds, probe.expectedPassageIds || []);
      } else {
        match = actual.outcome === probe.expectedOutcome;
      }
      perProbe.push({
        probeId: probe.probeId,
        question: probe.question,
        expectedOutcome: probe.expectedOutcome,
        expectedPassageIds: probe.expectedPassageIds || null,
        actualOutcome: actual.outcome,
        actualPassageIds: actual.passageIds,
        actualReceiptLine: raw.receiptLine,
        actualAbstainMsg: raw.abstainMsg,
        actualSources: raw.sources,
        match,
      });
      log(probe.probeId, "->", actual.outcome, match ? "MATCH" : "MISS");
    }

    const hits = perProbe.filter((p) => p.match).length;
    const total = perProbe.length;

    receipt = {
      generatedAt: new Date().toISOString(),
      korpusVersion: corpus.version,
      manifestSha256: corpus.manifestSha256,
      manifestSha256Source: "corpus.json (read fresh from disk this run, not hardcoded in this script)",
      engineVersion: "well.js v0 (retrieval only, BM25-ish, unmodified)",
      freezeMethod:
        "headless Chrome via raw CDP against the live, unmodified index.html/well.js served locally; " +
        "DOM-level submit + read-back only, no scoring logic reimplemented. " + RAF_PATCH_NOTE,
      chromeExecutable: chromePath,
      probesFile: path.relative(SITE_DIR, PROBES_PATH),
      probes: perProbe,
      summary: {
        total,
        hits,
        misses: total - hits,
        label: `${hits}/${total} matched`,
      },
      chip: "RECORDED",
    };
  } finally {
    if (cdp) cdp.close();
    await killChrome(chromeProc);
    await rm(userDataDir, { recursive: true, force: true }).catch(() => {});
    await new Promise((resolve) => server.close(resolve));
  }

  await writeFile(RECEIPT_PATH, JSON.stringify(receipt, null, 2) + "\n", "utf8");
  log("wrote", RECEIPT_PATH, "->", receipt.summary.label);
}

main().catch((err) => {
  log("FATAL:", err && err.stack ? err.stack : err);
  process.exitCode = 1;
});
