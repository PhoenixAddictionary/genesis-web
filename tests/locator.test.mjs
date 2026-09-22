/* Tests for locator.js — run: node --test tests/locator.test.mjs

   These exercise the shipped locator.js bytes against the shipped corpus.json
   bytes. There is no fixture corpus and no second copy of the parser: a test
   that passes against its own private copy of the data proves nothing about
   what the site serves.

   The load-bearing cases, in the order the diagnosis asked for them:
     - the frozen negative controls still parse as NON-addresses;
     - the exact question that failed Stage 1 now resolves;
     - ambiguous and unresolvable addresses abstain instead of guessing;
     - every address the corpus publishes round-trips to its own passage. */

import { test } from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const require = createRequire(import.meta.url);
const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const L = require(join(ROOT, "locator.js"));
const corpus = JSON.parse(readFileSync(join(ROOT, "corpus.json"), "utf8"));
const probes = JSON.parse(readFileSync(join(ROOT, "probes", "korpus-0.3.json"), "utf8"));
const index = L.buildIndex(corpus);

const locOf = (i) => corpus.passages[i].loc;
const idOf = (i) => corpus.passages[i].id;
const run = (q) => L.resolve(index, L.parse(index, q));

/* well.js's STOP list, verbatim. It deliberately does NOT hold "say"/"about":
   it feeds the BM25 index, so adding words there would move every score in the
   korpus. Copying it exactly is what makes the scaffolding test below real --
   a friendlier tokenizer here would filter those words itself and the test
   would pass without locator.js doing anything. */
const STOP = new Set(("a an and are as at be but by for from had has have i if in into is it its me my " +
  "no not of on or our so that the their them then there these they this to us was we were what when " +
  "where which who whom why will with would you your can could shall should do does did how am").split(" "));
const tokenize = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, " ").split(" ")
  .filter((w) => w.length >= 2 && !STOP.has(w));

/* ---------- 1. the corpus is the only source of addresses ---------- */

test("every passage has a parseable address", () => {
  assert.equal(index.unaddressable.length, 0,
    `unaddressable locs: ${index.unaddressable.map(locOf).join(", ")}`);
});

test("work names are derived from the corpus, not hardcoded", () => {
  assert.ok(index.workNames.includes("genesis"));
  assert.ok(index.workNames.includes("tao te ching"));
  assert.ok(index.workNames.length >= 10);
});

/* ---------- 2. negative controls: a bare work name is not an address ---------- */

test("frozen probe questions contain no address", () => {
  for (const p of probes.probes) {
    assert.equal(L.parse(index, p.question), null,
      `probe ${p.probeId} must stay lexical: ${JSON.stringify(p.question)}`);
  }
});

test("near-miss-genesis stays a non-address", () => {
  // The one the corpus deliberately lets miss: "genesis" with no number.
  assert.equal(L.parse(index, "what happened in the beginning according to genesis?"), null);
});

test("the contested pair question contains no address", () => {
  assert.equal(L.parse(index, "is the self eternal or does it return to dust?"), null);
});

test("bare work names are never addresses", () => {
  for (const w of index.workNames) {
    assert.equal(L.parse(index, `what does ${w} say about water?`), null, `bare "${w}"`);
  }
});

/* ---------- 3. the Stage-1 failure now resolves ---------- */

const STAGE1 = "What structural patterns of naming, separation, patience, and discovered value " +
  "appear in Genesis 1–3, without turning them into moral ranking or authority over people or agents?";

test("Stage-1 question resolves to exactly Genesis 1, 2 and 3", () => {
  const r = run(STAGE1);
  assert.equal(r.outcome, "LOCATOR_HIT");
  assert.deepEqual(r.indices.map(idOf), ["kjv:genesis-1", "kjv:genesis-2", "kjv:genesis-3"]);
});

test("Stage-1 question still carries an unanswered lens", () => {
  const addr = L.parse(index, STAGE1);
  const lens = L.lensOf(STAGE1, addr, (s) => tokenize(s));
  assert.ok(lens.length > 0, "the interpretive half must remain visible as unanswered");
  assert.ok(lens.includes("patience"));
  assert.ok(!lens.includes("genesis"), "the address must be removed before the lens is read");
});

/* ---------- 4. ordinary addressing ---------- */

test("single chapter", () => {
  assert.deepEqual(run("Genesis 1").indices.map(idOf), ["kjv:genesis-1"]);
  assert.deepEqual(run("Tao Te Ching 72").indices.map(idOf), ["tao:tao-te-ching-72"]);
});

test("a chapter number is whole: 7 does not match 72", () => {
  assert.deepEqual(run("Tao Te Ching 7").indices.map(idOf), ["tao:tao-te-ching-7"]);
});

test("ranges expand, in ascii and en-dash form", () => {
  for (const q of ["Genesis 1-3", "Genesis 1–3", "genesis 1 - 3"]) {
    assert.deepEqual(run(q).indices.map(idOf),
      ["kjv:genesis-1", "kjv:genesis-2", "kjv:genesis-3"], q);
  }
});

test("an exact ranged address wins over range expansion", () => {
  // "Isha Upanishad 1-5" is one passage's own address, not chapters 1..5.
  const r = run("Isha Upanishad 1-5");
  assert.equal(r.outcome, "LOCATOR_HIT");
  assert.equal(r.indices.length, 1);
  assert.equal(locOf(r.indices[0]), "Isha Upanishad 1-5");
});

test("sub-addresses pull their disambiguated siblings together", () => {
  const r = run("Bhagavad Gita 13.4");
  assert.equal(r.outcome, "LOCATOR_HIT");
  assert.ok(r.indices.length >= 2);
  for (const i of r.indices) assert.match(locOf(i), /^Bhagavad Gita 13\.4( \(\d+\))?$/);
});

test("a unique work-name suffix resolves", () => {
  assert.equal(run("gita 2.2").outcome, "LOCATOR_HIT");
});

test("the address may sit anywhere in the sentence", () => {
  assert.deepEqual(run("read genesis 1 please").indices.map(idOf), ["kjv:genesis-1"]);
  assert.deepEqual(run("genesis 1").indices.map(idOf), ["kjv:genesis-1"]);
});

test("the address quoted back is the address, not the sentence around it", () => {
  // Measured defect, first browser A/B run 2026-09-22: the card read
  // 'addressed as "what does genesis 1"' because the raw regex span was quoted.
  for (const [q, want] of [
    ["what does Genesis 1 say about light?", "genesis 1"],
    ["read genesis 1 please", "genesis 1"],
    ["Genesis 1 - 3", "genesis 1-3"],
    ["gita 2.2", "bhagavad gita 2.2"],   // canonical name, so the reader sees what was read
  ]) {
    assert.equal(L.parse(index, q).raw, want, q);
  }
});

test("an ambiguous reference is quoted in the reader's own words", () => {
  // "upanishad" is not a work; echoing a canonical name here would put words
  // in the reader's mouth and hide which of the four was meant.
  assert.equal(L.parse(index, "upanishad 1.1").raw, "upanishad 1.1");
});

test("request scaffolding is not reported as an unanswered question", () => {
  const q = "what does Genesis 1 say about light?";
  const lens = L.lensOf(q, L.parse(index, q), (s) => tokenize(s));
  assert.deepEqual(lens, ["light"]);
});

/* ---------- 5. abstention instead of guessing ---------- */

test("an ambiguous work name abstains and names the candidates", () => {
  const r = run("upanishad 1.1");
  assert.equal(r.outcome, "LOCATOR_AMBIGUOUS_WORK");
  assert.ok(r.candidates.length > 1);
  assert.ok(r.candidates.every((c) => c.endsWith("upanishad")));
});

test("an address outside the corpus abstains and shows what is addressable", () => {
  const r = run("Genesis 99");
  assert.equal(r.outcome, "LOCATOR_NOT_IN_CORPUS");
  assert.deepEqual(r.available, ["1", "2", "3"]);
});

test("an address that is too broad abstains rather than selecting three of many", () => {
  const r = run("Bhagavad Gita 2");
  assert.equal(r.outcome, "LOCATOR_TOO_BROAD");
  assert.ok(r.count > L.MAX_ADDRESSED);
  assert.equal(r.limit, 3);
});

test("no outcome ever carries a placeholder passage", () => {
  for (const q of ["Genesis 99", "upanishad 1.1", "Bhagavad Gita 2", "Genesis 1"]) {
    const r = run(q);
    assert.ok(!("indices" in r) || r.indices.every((i) => corpus.passages[i] !== undefined), q);
    assert.ok(!("passages" in r), "an unresolved address produces no passage object at all");
  }
});

/* ---------- 6. round trip: the corpus can address itself ---------- */

test("every published address resolves to its own passage, within the cap", () => {
  const failures = [];
  corpus.passages.forEach((p, i) => {
    const bare = p.loc.replace(/\s+\(\d+\)$/, "");
    const r = run(bare);
    if (!r || r.outcome !== "LOCATOR_HIT") { failures.push(`${p.loc} -> ${r && r.outcome}`); return; }
    if (!r.indices.includes(i)) failures.push(`${p.loc} -> resolved without itself`);
    if (r.indices.length > L.MAX_ADDRESSED) failures.push(`${p.loc} -> ${r.indices.length} > cap`);
  });
  assert.deepEqual(failures, [], failures.slice(0, 10).join("; "));
});

test("resolution is order-independent and repeatable", () => {
  const a = run("Genesis 1-3").indices;
  const b = run("Genesis 1-3").indices;
  assert.deepEqual(a, b);
  assert.deepEqual(a, [...a].sort((x, y) => x - y));
});
