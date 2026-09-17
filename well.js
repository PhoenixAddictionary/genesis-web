/* GENESIS well prototype v5 — progressive enhancement only.
   The page reads fully without this file (GX-005 invariant).
   No storage, no network, no inserted latency: every transition is
   user-initiated; motion runs only under prefers-reduced-motion: no-preference. */

(function () {
  "use strict";
  document.documentElement.classList.add("js");

  var motionOK = function () {
    return window.matchMedia("(prefers-reduced-motion: no-preference)").matches;
  };

  /* ================= terminal ================= */
  var form = document.getElementById("ask-form");
  var input = document.getElementById("ask-input");
  var line = document.getElementById("term-line");
  var out = document.getElementById("term-out");

  // micro-response: the underline breathes with each keystroke
  var typingTimer = null;
  if (input && line) {
    input.addEventListener("input", function () {
      line.classList.add("typing");
      clearTimeout(typingTimer);
      typingTimer = setTimeout(function () { line.classList.remove("typing"); }, 260);
    });
  }

  // example questions: plain text without JS, fill-the-prompt buttons with it
  if (input) {
    document.querySelectorAll(".term-pills .suggestion").forEach(function (el) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "suggestion";
      btn.textContent = el.textContent;
      btn.addEventListener("click", function () {
        input.value = btn.textContent;
        input.dispatchEvent(new Event("input"));
        input.focus();
      });
      el.replaceWith(btn);
    });
  }

  function print(cls, text) {
    var p = document.createElement("p");
    p.className = cls;
    p.textContent = text;
    out.appendChild(p);
    return p;
  }

  /* ---- engine v0: retrieval only, in-browser (docs/engine-api-contract.md) ----
     Sources render FIRST; prose is never composed; weak retrieval emits typed
     abstentions. Sources or silence — the governed void, enforced live. */
  var CORPUS = { data: null, promise: null };
  var lastQuestion = "";
  var STOP = {};
  ("a an and are as at be but by for from had has have i if in into is it its me my no not of on or " +
   "our so that the their them then there these they this to us was we were what when where which who " +
   "whom why will with would you your can could shall should do does did how am").split(" ")
    .forEach(function (w) { STOP[w] = 1; });

  function tokenize(s, expand) {
    var out2 = [];
    s.toLowerCase().replace(/[^a-z0-9]+/g, " ").split(" ").forEach(function (w) {
      if (w.length < 2 || STOP[w]) return;
      out2.push(w);
      if (expand === false) return;
      // light stemming, applied identically at index and query time
      var v = w.replace(/(ness|ment)$/, "").replace(/i$/, "y");
      if (v !== w && v.length > 2 && !STOP[v]) out2.push(v);
      var p = w.slice(0, -1);
      if (/s$/.test(w) && !/ss$/.test(w) && w.length > 3 && !STOP[p]) out2.push(p);
    });
    return out2;
  }

  function loadCorpus() {
    if (CORPUS.promise) return CORPUS.promise;
    CORPUS.promise = fetch("corpus.json").then(function (r) {
      if (!r.ok) throw new Error("corpus " + r.status);
      return r.json();
    }).then(function (c) {
      var idx = {}, dl = [], total = 0;
      c.passages.forEach(function (p, i) {
        var toks = tokenize(p.text + " " + p.loc);
        dl[i] = toks.length;
        total += toks.length;
        var tf = {};
        toks.forEach(function (t) { tf[t] = (tf[t] || 0) + 1; });
        Object.keys(tf).forEach(function (t) { (idx[t] = idx[t] || []).push([i, tf[t]]); });
      });
      c._idx = idx;
      c._dl = dl;
      c._avgdl = total / c.passages.length;
      CORPUS.data = c;
      return c;
    });
    return CORPUS.promise;
  }

  // spine/spine.jsonl (GX-005): a frozen, curated-only set of real
  // genesis.event.v1 records -- see spine/README.md. This is the ONLY place
  // this file is ever read; the browser never appends to it, never grows it,
  // and never sends it anything -- a fake, growing spine is exactly what
  // this project's own constitution forbids ("no claim without a receipt").
  // Fetch failure fails closed: SPINE.events stays {} and no question is
  // ever claimed RECORDED without it (see resolveSpineMatch below).
  var SPINE = { events: null, promise: null };
  function loadSpine() {
    if (SPINE.promise) return SPINE.promise;
    SPINE.promise = fetch("spine/spine.jsonl").then(function (r) {
      if (!r.ok) throw new Error("spine " + r.status);
      return r.text();
    }).then(function (text) {
      var events = {};
      text.split("\n").forEach(function (line) {
        line = line.trim();
        if (!line) return;
        try {
          var ev = JSON.parse(line);
          if (ev && ev.eventId) events[ev.eventId] = ev;
        } catch (e) { /* a malformed line is never fabricated into an event */ }
      });
      SPINE.events = events;
      return events;
    }).catch(function () {
      SPINE.events = {};
      return SPINE.events;
    });
    return SPINE.promise;
  }

  // spine/live.jsonl (Einklinken E2, v1): a small, machine-generated log --
  // one line per push to main, written by a GitHub Action on Build-Zeit
  // cadence (Owner-Akt 2, 2026-09-17), never on the visitor's own clock and
  // never fetched from anywhere but this same static file. Same fail-closed
  // rule as loadSpine above: a fetch failure or an empty file leaves the
  // static "live now: quiet" text exactly as it already reads in the HTML --
  // never overwritten with an invented status. v1 shows only two classes
  // ("gast" / "projekt"), see spine/schemas/genesis.live-tick.v1.schema.json
  // for why a finer split isn't attempted yet.
  function loadLiveTick() {
    return fetch("spine/live.jsonl").then(function (r) {
      if (!r.ok) throw new Error("live " + r.status);
      return r.text();
    }).then(function (text) {
      var last = null;
      text.split("\n").forEach(function (line) {
        line = line.trim();
        if (!line) return;
        try {
          var tick = JSON.parse(line);
          if (tick && tick.schema === "genesis.live-tick.v1") last = tick;
        } catch (e) { /* a malformed line is never fabricated into a tick */ }
      });
      return last;
    }).catch(function () { return null; });
  }

  function relativeTime(iso) {
    var then = new Date(iso).getTime();
    if (isNaN(then)) return null;
    var seconds = Math.max(0, Math.round((Date.now() - then) / 1000));
    var units = [
      [31536000, "year"], [2592000, "month"], [86400, "day"],
      [3600, "hour"], [60, "minute"],
    ];
    for (var i = 0; i < units.length; i++) {
      var n = Math.floor(seconds / units[i][0]);
      if (n >= 1) return n + " " + units[i][1] + (n === 1 ? "" : "s") + " ago";
    }
    return "moments ago";
  }

  function renderLiveStatus() {
    var el = document.getElementById("live-status");
    if (!el) return;
    loadLiveTick().then(function (tick) {
      if (!tick) return; // stays "live now: quiet -- no engine connected"
      var rel = relativeTime(tick.occurredAt);
      if (!rel) return; // an unparseable timestamp is never displayed as if it were real
      var who = tick.class === "gast" ? ", from a guest contributor" : "";
      el.textContent = "live now: last act " + rel + who + ". nothing here is invented.";
    });
  }

  function search(c, q) {
    var toks = tokenize(q);
    var K1 = 1.5, B = 0.75, N = c.passages.length;
    var scores = {}, matched = {}, matchedTerms = {};
    toks.forEach(function (t) {
      var post = c._idx[t];
      if (!post) return;
      var idf = Math.log(1 + (N - post.length + 0.5) / (post.length + 0.5));
      post.forEach(function (e) {
        var i = e[0], tf = e[1];
        scores[i] = (scores[i] || 0) +
          idf * (tf * (K1 + 1)) / (tf + K1 * (1 - B + B * c._dl[i] / c._avgdl));
        matched[i] = (matched[i] || 0) + 1;
        // same loop, same posting list -- just also keeping which term hit,
        // for "why this came up" (W4-3): a receipt, not a new matching pass.
        (matchedTerms[i] = matchedTerms[i] || []).push(t);
      });
    });
    return {
      toks: toks,
      hits: Object.keys(scores).map(function (i) {
        return { i: +i, score: scores[i], matched: matched[i], terms: matchedTerms[i] || [] };
      }).sort(function (a, b) { return b.score - a.score; })
    };
  }

  function excerpt(text) {
    if (text.length <= 260) return text;
    var cut = text.slice(0, 260);
    return cut.slice(0, cut.lastIndexOf(" ")) + " …";
  }

  function srcTitle(c, sid) {
    for (var k = 0; k < c.sources.length; k++) {
      if (c.sources[k].sourceId === sid) return c.sources[k].title;
    }
    return sid;
  }

  function chipEl(kind, label) {
    var s = document.createElement("span");
    s.className = "chip chip-" + kind;
    s.title = kind === "recorded"
      ? "About this record: written down and hashed — its existence and exact wording are checkable. Correctness is not claimed."
      : "About this record: an idea written down — nothing built, nothing verified. This describes the record, not whether the idea is good.";
    s.textContent = label;
    return s;
  }

  // W4-5: CONTESTED, a real curated pair -- Owner ruling R2 (2026-09-16):
  // outcome stays ANSWERED, both sourced positions render side by side,
  // labeled contested; this is NOT a CONTESTED abstention and picks no
  // winner. Both ids below were verified live against this exact engine +
  // korpus 0.3 (raw-CDP Chrome, same technique as probes/freeze_probes.mjs):
  // the question retrieves both solidly (score 7.6 and 6.2, well over the
  // >=2.0 solid-hit floor) in the real top hits -- see the go() function
  // below, which re-checks this live on every submit rather than trusting
  // this comment. If korpus content ever changes and one id drops out of
  // the real results, contestedReady is false and this falls through to
  // the ordinary hit/abstain path instead of faking a position.
  var CONTESTED_QUESTION = "is the self eternal or does it return to dust?";
  var CONTESTED_PAIR = {
    a: {
      passageId: "upanishad:katha-upanishad-5-11-15",
      label: "The Katha Upanishad answers: the Self is eternal, one ruler within all things, untouched by the world it perceives."
    },
    b: {
      passageId: "kjv:ecclesiastes-12",
      label: "Ecclesiastes answers: the dust returns to the earth as it was — vanity of vanities, all is vanity."
    }
  };

  function findHitByPassageId(hits, passageId, c) {
    for (var i = 0; i < hits.length; i++) {
      if (c.passages[hits[i].i].id === passageId) return hits[i];
    }
    return null;
  }

  // W4-4: one curated follow-up per result, never generated per-question.
  // Every candidate here was verified against the real engine (this same
  // search()) before being added -- picked by the top hit's real source
  // when there is one (e.g. a Tao hit suggests a Tao-adjacent follow-up),
  // a single fixed default otherwise. This is the "single fixed curated
  // follow-up... if contextual selection is not clean to wire" escape
  // hatch the build plan allows, made slightly contextual because the
  // source is already sitting right there on the hit.
  var FOLLOWUP_BY_SOURCE = {
    tao: "what does the tao say about water?",
    upanishad: "what happens to the soul after death?",
    gita: "should i give up the fruits of my work?",
    kjv: CONTESTED_QUESTION
  };
  var FOLLOWUP_DEFAULT = "what happens to the soul after death?";
  // Distinct from every entry above and from FOLLOWUP_DEFAULT, so the
  // "never repeat the question just asked" swap below always lands on a
  // genuinely different question, verified against the real engine like
  // the others (see capture.py: real Tao/Upanishad/Ecclesiastes hits).
  var FOLLOWUP_FALLBACK = "what is emptiness?";

  // W4-6 (GX-005): the spine wiring -- the ONLY 4 curated questions that have
  // a real, receipted genesis.event.v1 behind them (spine/spine.jsonl, see
  // spine/README.md for the full mapping table and how to extend it safely).
  // Every other question -- the 3 pills, every other probe, any free-text
  // input -- must keep showing CONCEPT: this table only maps exact question
  // text to an eventId, it never decides the outcome by itself. Never add a
  // 5th entry here without also adding a live-outcome re-check branch to
  // resolveSpineMatch() below -- an unchecked mapping entry is exactly the
  // "trust the table blindly" failure this project's constitution forbids.
  var SPINE_QUESTION_MAP = {
    "what does the tao say about water?": "EVT-WELL-PROBE-HIT-TAO-WATER-001",
    "what happens to the soul after death?": "EVT-WELL-PROBE-HIT-UPANISHAD-SOUL-DEATH-001",
    "is the self eternal or does it return to dust?": "EVT-WELL-PROBE-CONTESTED-SELF-DUST-001",
    "how do i configure a kubernetes cluster?": "EVT-WELL-PROBE-NO-MATCH-KUBERNETES-001"
  };

  // Re-verifies the LIVE outcome this exact submit just produced against
  // what the frozen spine event actually recorded, every time -- never
  // trusts SPINE_QUESTION_MAP alone. If the korpus content ever changes and
  // a live result stops matching (e.g. a passage id drops out of the real
  // top hits), this returns null and the caller falls back to the ordinary
  // CONCEPT state instead of a stale RECORDED claim.
  function resolveSpineMatch(question, kind, c, top, hA, hB) {
    var norm = (question || "").trim().toLowerCase();
    var eventId = SPINE_QUESTION_MAP[norm];
    if (!eventId || !SPINE.events) return null;
    var ev = SPINE.events[eventId];
    // spine.jsonl failed to load, or doesn't contain this id: never fabricate
    // a match from the mapping table alone.
    if (!ev) return null;

    function topHasPassage(pid) {
      if (!c || !top) return false;
      for (var i = 0; i < top.length; i++) {
        if (c.passages[top[i].i].id === pid) return true;
      }
      return false;
    }

    if (eventId === "EVT-WELL-PROBE-HIT-TAO-WATER-001") {
      if (kind !== "hit" || !topHasPassage("tao:tao-te-ching-8")) return null;
      return { eventId: eventId, eventType: ev.eventType };
    }
    if (eventId === "EVT-WELL-PROBE-HIT-UPANISHAD-SOUL-DEATH-001") {
      if (kind !== "hit" || !topHasPassage("upanishad:katha-upanishad-5-6-10")) return null;
      return { eventId: eventId, eventType: ev.eventType };
    }
    if (eventId === "EVT-WELL-PROBE-CONTESTED-SELF-DUST-001") {
      if (kind !== "contested" || !hA || !hB || !c) return null;
      if (c.passages[hA.i].id !== CONTESTED_PAIR.a.passageId) return null;
      if (c.passages[hB.i].id !== CONTESTED_PAIR.b.passageId) return null;
      return { eventId: eventId, eventType: ev.eventType };
    }
    if (eventId === "EVT-WELL-PROBE-NO-MATCH-KUBERNETES-001") {
      if (kind !== "no_sources") return null;
      return { eventId: eventId, eventType: ev.eventType };
    }
    return null;
  }

  // III's additive glyph (Owner ruling R1): one fixed ring position per
  // curated eventId, placed in the gap the real 30 baked events already
  // leave open (they span --a:-55 .. --a:229.2; this sits past them, never
  // overlapping a real one). spineGlyphsAdded makes the add idempotent per
  // session -- the event already "happened" once; asking the same question
  // again never duplicates it, same real-world logic as a git/PR event
  // never firing twice.
  var SPINE_GLYPH_POSITION = {
    "EVT-WELL-PROBE-HIT-TAO-WATER-001":            { a: 245, r: 0.58 },
    "EVT-WELL-PROBE-HIT-UPANISHAD-SOUL-DEATH-001": { a: 262, r: 0.58 },
    "EVT-WELL-PROBE-CONTESTED-SELF-DUST-001":      { a: 279, r: 0.58 },
    "EVT-WELL-PROBE-NO-MATCH-KUBERNETES-001":      { a: 296, r: 0.58 }
  };
  var spineGlyphsAdded = {};

  // Adds exactly one glyph to Window III's peek ring for a real spine match
  // -- reuses the existing .rw-dot rendering mechanism fillPeek() already
  // built for the 30 baked events (same --a/--r positioning, same element
  // type), just a visually distinct kind (k-question, styles.css). Labeled
  // only by eventType -- never by the question text (Owner ruling R1).
  function addSpineGlyph(eventId, eventType) {
    if (!rwPeek || spineGlyphsAdded[eventId]) return;
    var ring = rwPeek.querySelector(".rw-peek-ring");
    var pos = SPINE_GLYPH_POSITION[eventId];
    if (!ring || !pos) return;
    var d = document.createElement("span");
    d.className = "rw-dot k-question";
    d.style.setProperty("--a", pos.a);
    d.style.setProperty("--r", pos.r);
    d.title = eventType;
    ring.appendChild(d);
    spineGlyphsAdded[eventId] = true;
  }

  function pickFollowup(question, topHit, c) {
    var candidate = FOLLOWUP_DEFAULT;
    if (topHit && c) {
      var src = c.passages[topHit.i].s;
      if (FOLLOWUP_BY_SOURCE[src]) candidate = FOLLOWUP_BY_SOURCE[src];
    }
    // never suggest the question the visitor just asked
    var asked = (question || "").trim().toLowerCase();
    if (candidate.trim().toLowerCase() === asked) candidate = FOLLOWUP_FALLBACK;
    return candidate;
  }

  function renderSource(c, h, into, selectCtx) {
    var p = c.passages[h.i];
    var d = document.createElement("div");
    d.className = "to-src";
    d.dataset.passageId = p.id;
    d.dataset.passageSha256 = p.sha256;

    // I -> II trace (W4-1): a visitor-initiated select surface, separate from
    // the native <details> below so no interactive control nests inside another.
    var sel = document.createElement("div");
    sel.className = "to-src-select";
    sel.setAttribute("role", "button");
    sel.tabIndex = 0;
    sel.setAttribute("aria-pressed", "false");
    sel.setAttribute("aria-label", "Select this source \u2014 trace it to the receipt in II");

    var x = document.createElement("p");
    x.className = "src-x";
    x.textContent = "\u201C" + excerpt(p.text) + "\u201D";
    var m = document.createElement("p");
    m.className = "src-m mono";
    m.textContent = "\u2014 " + p.loc + " \u00B7 " + srcTitle(c, p.s) +
      " \u00B7 sha256 " + p.sha256.slice(0, 8) + " \u00B7 score " + h.score.toFixed(1);
    sel.appendChild(x);
    sel.appendChild(m);
    d.appendChild(sel);

    // "why this came up" (W4-3): the real matched terms + BM25 score the
    // search() pass above already computed. No new scoring, no composed
    // explanation -- just the retrieval receipt, behind a native <details>.
    var why = document.createElement("details");
    why.className = "zoom src-why";
    var summary = document.createElement("summary");
    summary.textContent = "why this came up";
    why.appendChild(summary);
    var whyBody = document.createElement("div");
    whyBody.className = "zoom-body";
    var terms = document.createElement("p");
    terms.className = "receipt";
    var termList = (h.terms || []).join(", ");
    terms.textContent = "matched terms: " + (termList || "(no query term indexed for this passage)");
    var score = document.createElement("p");
    score.className = "receipt";
    score.textContent = "BM25 score: " + h.score.toFixed(4);
    whyBody.appendChild(terms);
    whyBody.appendChild(score);
    why.appendChild(whyBody);
    d.appendChild(why);

    into.appendChild(d);

    if (selectCtx) {
      var fire = function () { selectSource(selectCtx, h, d); };
      sel.addEventListener("click", fire);
      sel.addEventListener("keydown", function (ev) {
        if (ev.target !== sel) return;
        if (ev.key === "Enter" || ev.key === " " || ev.key === "Spacebar") {
          ev.preventDefault();
          fire();
        }
      });
    }
  }

  // W4-5 CONTESTED: renders both positions with the SAME renderSource() card
  // used everywhere else -- selection-to-trace (W4-1) and "why this came
  // up" (W4-3) keep working identically on a contested pair, because this
  // is not a parallel rendering path, just two real cards plus the plain
  // labeling copy naming each side in its own tradition's terms. Neither
  // side is ranked, scored against the other, or resolved into a third view.
  function renderContested(c, hA, hB, into, selectCtx) {
    var wrap = document.createElement("div");
    wrap.className = "to-contested";

    var note = document.createElement("p");
    note.className = "to-a to-contested-note";
    note.textContent = "two real sources answer this differently — shown " +
      "side by side, contested, neither picked as the winner:";
    wrap.appendChild(note);

    var labelA = document.createElement("p");
    labelA.className = "to-contested-label";
    labelA.textContent = CONTESTED_PAIR.a.label;
    wrap.appendChild(labelA);
    renderSource(c, hA, wrap, selectCtx);

    var labelB = document.createElement("p");
    labelB.className = "to-contested-label";
    labelB.textContent = CONTESTED_PAIR.b.label;
    wrap.appendChild(labelB);
    renderSource(c, hB, wrap, selectCtx);

    var closing = document.createElement("p");
    closing.className = "to-a";
    closing.textContent = "retrieval only — both passages are real sources; " +
      "nothing is composed on top, and neither is ranked above the other. (engine v0)";
    wrap.appendChild(closing);

    into.appendChild(wrap);
  }

  function printAbstain(type, text, into) {
    var d = document.createElement("p");
    d.className = "to-abstain";
    var t = document.createElement("span");
    t.className = "ab-type";
    t.textContent = "[" + type + "] ";
    d.appendChild(t);
    d.appendChild(document.createTextNode(text));
    into.appendChild(d);
  }

  function receiptLine(c, top) {
    var ids = top.map(function (h) {
      var p = c.passages[h.i];
      return p.id + "@" + p.sha256.slice(0, 8);
    }).join(" \u00B7 ");
    return "receipt \u2014 " + (ids ? "passages: " + ids : "no passage matched solidly") +
      " \u00B7 korpus " + c.version + " manifest " + c.manifestSha256.slice(0, 12) +
      " \u00B7 " + c.passageCount + " passages \u00B7 engine v0, retrieval only \u00B7 your question is not stored";
  }

  // I -> II trace (W4-1): selecting a source in I re-points II's one receipt
  // line at that exact passage -- id + full sha256 -- instead of the top-N
  // list. Additive only: deleting this (and the click wiring above) leaves
  // the static receiptLine() text in place, so II still makes sense alone.
  function receiptLineSelected(c, h) {
    var p = c.passages[h.i];
    // same truncation the page uses everywhere else for a hash (renderSource,
    // receiptLine, the footer's canon anchors) -- full sha256 is on the
    // passage object and in corpus.json for anyone who wants to check it.
    return "receipt \u2014 selected: " + p.id + " \u00B7 sha256 " + p.sha256.slice(0, 8) +
      " \u00B7 korpus " + c.version + " manifest " + c.manifestSha256.slice(0, 12) +
      " \u00B7 " + c.passageCount + " passages \u00B7 engine v0, retrieval only \u00B7 your question is not stored";
  }

  function selectSource(ctx, h, cardEl) {
    Array.prototype.forEach.call(ctx.into.querySelectorAll(".to-src"), function (s) {
      s.classList.remove("to-src-selected");
      var b = s.querySelector(".to-src-select");
      if (b) b.setAttribute("aria-pressed", "false");
    });
    cardEl.classList.add("to-src-selected");
    var self = cardEl.querySelector(".to-src-select");
    if (self) self.setAttribute("aria-pressed", "true");
    var rc = ctx.rwEng.querySelector(".to-rcpt");
    if (rc) rc.textContent = receiptLineSelected(ctx.c, h);
  }

  // the descent: user-initiated cinematic pull (never autoplay)
  var pulling = false;
  function cancelPull() { pulling = false; }
  ["wheel", "touchstart", "keydown"].forEach(function (ev) {
    window.addEventListener(ev, cancelPull, { passive: true });
  });

  function pullDown(question) {
    var world = document.getElementById("world");
    if (!world) return;
    if (!motionOK()) {
      world.scrollIntoView({ behavior: "auto", block: "start" });
      return;
    }
    // the question sinks ahead of you
    if (question) {
      var q = document.createElement("p");
      q.className = "sinking-q";
      q.textContent = question;
      document.body.appendChild(q);
      q.animate(
        [
          { transform: "translateX(-50%) translateY(0) scale(1)", opacity: 1 },
          { transform: "translateX(-50%) translateY(46vh) scale(0.72)", opacity: 0 }
        ],
        { duration: 3800, easing: "cubic-bezier(0.45, 0, 0.35, 1)", fill: "forwards" }
      ).onfinish = function () { q.remove(); };
    }
    // slow pull to the world; any user input hands control back instantly
    var startY = window.scrollY;
    var endY = world.getBoundingClientRect().top + window.scrollY;
    var t0 = null;
    var DUR = 4600;
    pulling = true;
    function ease(t) { return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2; }
    function step(ts) {
      if (!pulling) return;
      if (t0 === null) t0 = ts;
      var t = Math.min((ts - t0) / DUR, 1);
      window.scrollTo(0, startY + (endY - startY) * ease(t));
      if (t < 1) requestAnimationFrame(step);
      else pulling = false;
    }
    requestAnimationFrame(step);
  }

  /* ================= the first wiring: three masks over the empty terminal =================
     The result does not dump into the blessed prompt. It pops as I sources,
     II the engine (good for / driving / a first learning), III the living picture.
     That is where the verdrahtung starts. Descent stays visitor-chosen. */
  var terminal = document.getElementById("terminal");
  var rw = document.getElementById("result-windows");
  var rwQ = document.getElementById("rw-q");
  var rwSrc = document.getElementById("rw-src-body");
  var rwEng = document.getElementById("rw-eng-body");
  var rwPic = document.getElementById("rw-pic-body");
  var rwPeek = document.getElementById("rw-peek");
  var rwEnter = document.getElementById("rw-enter");
  var rwAgain = document.getElementById("rw-again");
  var rwFollowup = document.getElementById("rw-followup");
  var peekFilled = false;

  // Mobile bug (owner-reported 2026-09-17): .rw is position: absolute so it
  // never contributes to #terminal's height. On mobile the three masks stack
  // in one column and grow far taller than #terminal's own 100vh box, so the
  // tail of the result painted straight over #shaft's "your question ..."
  // line below it -- two sections' text visibly overlapping. #terminal needs
  // to actually grow to contain .rw (matching the "page scrolls to reveal
  // the rest" intent already stated above for the desktop inset fix), and
  // .rw's content keeps growing asynchronously as sources/engine/picture
  // fill in, so a one-shot measurement in openWindows() isn't enough.
  var rwHeightObserver = (typeof ResizeObserver !== "undefined")
    ? new ResizeObserver(function () { syncTerminalHeight(); })
    : null;
  function syncTerminalHeight() {
    if (!terminal || !rw || rw.hidden) return;
    var rwRect = rw.getBoundingClientRect();
    var termRect = terminal.getBoundingClientRect();
    var needed = (rwRect.top - termRect.top) + rwRect.height + 24;
    terminal.style.minHeight = Math.max(needed, termRect.height) + "px";
  }

  function fillPeek() {
    if (!rwPeek || peekFilled) return;
    var center = document.createElement("div");
    center.className = "rw-peek-center";
    var ring = document.createElement("div");
    ring.className = "rw-peek-ring";
    document.querySelectorAll("#pl-ring .pl-ev").forEach(function (ev) {
      var d = document.createElement("span");
      var kind = (ev.className.match(/k-\w+/) || ["k-commit"])[0];
      d.className = "rw-dot " + kind;
      d.setAttribute("style", ev.getAttribute("style") || "");
      d.title = ev.getAttribute("title") || "";
      ring.appendChild(d);
    });
    rwPeek.appendChild(ring);
    rwPeek.appendChild(center);
    peekFilled = true;
  }

  function dlPair(dl, dtText, dds) {
    var dt = document.createElement("dt");
    dt.textContent = dtText;
    dl.appendChild(dt);
    dds.forEach(function (item) {
      var dd = document.createElement("dd");
      if (typeof item === "string") dd.textContent = item;
      else dd.appendChild(item);
      dl.appendChild(dd);
    });
  }

  function nodeWithChip(before, kind, label, after) {
    var span = document.createElement("span");
    if (before) span.appendChild(document.createTextNode(before));
    span.appendChild(chipEl(kind, label));
    if (after) span.appendChild(document.createTextNode(after));
    return span;
  }

  // W4-2 / W4-6: the II -> III affordance, in one place. fillEngine's driving
  // row and fillPicture's conditional both read this SAME object -- so the
  // "CONCEPT"/"RECORDED" state and III's copy each exist once in this file,
  // not as two hardcoded copies that could silently drift apart. fillEngine
  // sets it fresh on every call from resolveSpineMatch()'s live-reverified
  // result (never trusted from a stale prior call) and immediately calls
  // fillPicture() so III is always in sync with what II just decided. Only
  // the 4 curated questions in SPINE_QUESTION_MAP can ever produce RECORDED
  // here -- everything else stays CONCEPT, exactly as before GX-005.
  var engineDriving = { kind: "CONCEPT", glyphId: null, eventType: null };

  var GOOD_FOR = {
    hit: ["the passages themselves — nothing composed on top",
          "a receipt you can check against this korpus"],
    contested: ["two sourced positions, side by side — a contested case, answered without picking a winner",
                "a receipt for each position, so you can check both against this korpus"],
    abstain: ["a typed non-answer instead of a guess",
              "the boundary of the korpus, named rather than smoothed over"],
    pending: ["the passages, when they land — nothing composed on top",
              "a receipt bound to this korpus"]
  };
  var EVENT_NAME = {
    hit: "QUESTION_ANSWERED",
    // R2: a contested case still resolves to ANSWERED (mapped positions,
    // labeled contested) -- never a separate CONTESTED abstention.
    contested: "QUESTION_ANSWERED",
    abstain: "QUESTION_ABSTAINED",
    pending: "a question event"
  };

  function fillEngine(kind, c, top, spineMatch) {
    rwEng.textContent = "";
    var kicker = document.createElement("p");
    kicker.className = "rw-kicker";
    kicker.textContent = "the first wiring — question to korpus to world";
    rwEng.appendChild(kicker);

    var dl = document.createElement("dl");
    dl.className = "rw-dl";
    dlPair(dl, "good for", GOOD_FOR[kind] || GOOD_FOR.pending);

    // this is the one place that decides engineDriving, read by
    // fillPicture() right after. spineMatch comes from resolveSpineMatch(),
    // already re-verified against this exact submit's live outcome -- never
    // trusted here a second time.
    var evName = (spineMatch && spineMatch.eventType) || EVENT_NAME[kind] || EVENT_NAME.pending;
    engineDriving = spineMatch
      ? { kind: "RECORDED", glyphId: spineMatch.eventId, eventType: spineMatch.eventType }
      : { kind: "CONCEPT", glyphId: null, eventType: null };
    dlPair(dl, "driving", [
      nodeWithChip(evName + "  ", engineDriving.kind.toLowerCase(), engineDriving.kind,
        engineDriving.kind === "CONCEPT"
          ? " — not on the ring until the spine feeds"
          : " · " + engineDriving.glyphId)
    ]);

    dlPair(dl, "a first learning", [
      "the path is visible: question → these sources → the world below",
      "the engine is drilled by being used. your question is not stored."
    ]);

    // Window II polish: probes/receipt-korpus-0.3.json is a real, frozen
    // artifact (10/10 locators matched, manifest 409032026696…, generated
    // 2026-09-16) -- read once at build time here, not fetched live (this
    // page's only network call stays corpus.json). One line, not a panel.
    dlPair(dl, "last probe", [
      "10/10 locators matched · manifest 409032026696… (probes/receipt-korpus-0.3.json)"
    ]);
    rwEng.appendChild(dl);

    if (c && kind !== "pending") {
      var rc = document.createElement("p");
      rc.className = "to-rcpt";
      rc.textContent = receiptLine(c, top || []);
      rwEng.appendChild(rc);
    }

    fillPicture();
  }

  function fillPicture() {
    rwPic.textContent = "";
    var a = document.createElement("p");
    a.className = "rw-pic-lead";
    a.textContent = "30 recorded events. already real.";
    rwPic.appendChild(a);

    if (engineDriving.kind === "RECORDED" && engineDriving.glyphId) {
      // W4-6 (GX-005): a real, live-reverified spine event -- add exactly
      // one glyph to III's peek ring (idempotent per session, see
      // addSpineGlyph) and say so honestly, labeled by eventType only.
      addSpineGlyph(engineDriving.glyphId, engineDriving.eventType);
      var r = document.createElement("p");
      r.className = "rw-pic-note";
      r.appendChild(document.createTextNode(
        "this question just became one more real event on the ring — "));
      r.appendChild(chipEl("recorded", "RECORDED"));
      r.appendChild(document.createTextNode(" " + engineDriving.glyphId));
      rwPic.appendChild(r);
      return;
    }
    var b = document.createElement("p");
    b.className = "rw-pic-note";
    b.appendChild(document.createTextNode(
      "this result is not on the ring yet — question events need the spine. "));
    b.appendChild(chipEl("concept", "CONCEPT"));
    rwPic.appendChild(b);
  }

  function openWindows(question) {
    if (!rw || !terminal) return;
    terminal.classList.add("has-result");
    if (rwQ) {
      rwQ.textContent = "";
      if (question) {
        var mark = document.createElement("span");
        mark.className = "rw-q-mark";
        mark.textContent = "› ";
        rwQ.appendChild(mark);
        rwQ.appendChild(document.createTextNode(question));
      }
    }
    fillPeek();
    // III's content now comes from fillEngine() -> fillPicture() (W4-2), so
    // it is not filled here separately; the submit handler calls fillEngine
    // synchronously right after openWindows(), before any paint happens.
    rw.hidden = false;
    rw.classList.remove("rw-pop");
    void rw.offsetWidth;
    rw.classList.add("rw-pop");
    window.dispatchEvent(new Event("scroll"));
    syncTerminalHeight();
    if (rwHeightObserver) rwHeightObserver.observe(rw);
  }

  function closeWindows() {
    if (!rw || !terminal) return;
    rw.hidden = true;
    rw.classList.remove("rw-pop");
    terminal.classList.remove("has-result");
    form.classList.remove("asked");
    if (rwSrc) rwSrc.textContent = "";
    if (rwEng) rwEng.textContent = "";
    if (out) out.textContent = "";
    setFollowup(null);
    if (input) input.focus();
    window.dispatchEvent(new Event("scroll"));
    if (rwHeightObserver) rwHeightObserver.unobserve(rw);
    terminal.style.minHeight = "";
  }

  function announce(text) {
    if (out) out.textContent = text;
  }

  // W4-4: the one follow-up affordance. Not a chat -- selecting it clears
  // the current result and refills+resubmits, exactly one question at a
  // time, same as "ask again" plus a real question already in the box.
  function setFollowup(text) {
    if (!rwFollowup) return;
    if (!text) {
      rwFollowup.hidden = true;
      rwFollowup.textContent = "";
      rwFollowup.removeAttribute("data-question");
      return;
    }
    rwFollowup.dataset.question = text;
    rwFollowup.textContent = "⇝ ask next — " + text;
    rwFollowup.hidden = false;
  }

  if (rwEnter) {
    rwEnter.addEventListener("click", function (ev) {
      ev.preventDefault();
      pullDown(lastQuestion);
    });
  }
  if (rwAgain) {
    rwAgain.addEventListener("click", function () { closeWindows(); });
  }
  if (rwFollowup) {
    // "does what ask again already does: clears and refills... and
    // re-runs the same submit flow" -- one click, one new result, never a
    // second click required and never appended to a running thread.
    rwFollowup.addEventListener("click", function () {
      var q = rwFollowup.dataset.question || "";
      if (!q || !input || !form) return;
      input.value = q;
      input.dispatchEvent(new Event("input"));
      if (form.requestSubmit) form.requestSubmit();
      else form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
    });
  }
  document.addEventListener("keydown", function (ev) {
    if (ev.key === "Escape" && terminal && terminal.classList.contains("has-result")) {
      closeWindows();
    }
  });

  if (form && input && out) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var question = input.value.trim();
      lastQuestion = question;
      form.classList.add("asked");
      input.value = "";
      var toks = tokenize(question, false);
      openWindows(question);
      rwSrc.textContent = "";
      fillEngine(toks.length ? "pending" : "abstain", null, []);

      if (!question || toks.length === 0) {
        printAbstain("AMBIGUOUS", "one clarifying question, instead of a weak answer: " +
          "which thing should I look for \u2014 can you give me one concrete word?", rwSrc);
        fillEngine("abstain", null, []);
        input.value = question;
        setFollowup(pickFollowup(question, null, null));
        announce("AMBIGUOUS — one clarifying question");
        return;
      }

      var status = document.createElement("p");
      status.className = "to-a to-status";
      status.textContent = "reading the korpus \u2026";
      rwSrc.appendChild(status);
      announce("reading the korpus");

      Promise.all([loadCorpus(), loadSpine()]).then(function (loaded) {
        var c = loaded[0];
        status.textContent = "reading " + c.passageCount + " passages \u2026";
        fillEngine("pending", c, []);
        var go = function () {
          var res = search(c, question);
          status.remove();

          // W4-5 CONTESTED: only for the one curated, pre-verified question,
          // and only if the real live search still puts both real passages
          // up with a solid score -- re-checked every time, never assumed.
          var isContestedQ = question.trim().toLowerCase() === CONTESTED_QUESTION;
          var hA = isContestedQ ? findHitByPassageId(res.hits, CONTESTED_PAIR.a.passageId, c) : null;
          var hB = isContestedQ ? findHitByPassageId(res.hits, CONTESTED_PAIR.b.passageId, c) : null;
          var contestedReady = !!(hA && hB && hA.score >= 2.0 && hB.score >= 2.0);

          var top = res.hits.slice(0, 3);
          var solid = top.length > 0 &&
            top[0].matched >= Math.ceil(toks.length / 2) && top[0].score >= 2.0;
          if (contestedReady) {
            var contestedCtx = { c: c, into: rwSrc, rwEng: rwEng };
            renderContested(c, hA, hB, rwSrc, contestedCtx);
            fillEngine("contested", c, [hA, hB], resolveSpineMatch(question, "contested", c, null, hA, hB));
            setFollowup(pickFollowup(question, null, c));
            announce("ANSWERED — contested: two sourced positions, neither resolved");
          } else if (!solid) {
            var names = c.sources.map(function (s) { return s.title; }).join("; ");
            printAbstain("NO_SOURCES", "I found nothing solid for this. My sources are: " +
              names + " \u2014 this question seems to live outside them.", rwSrc);
            fillEngine("abstain", c, [], resolveSpineMatch(question, "no_sources", c, null, null, null));
            setFollowup(pickFollowup(question, null, c));
            announce("NO_SOURCES");
          } else {
            var selectCtx = { c: c, into: rwSrc, rwEng: rwEng };
            top.forEach(function (h) { renderSource(c, h, rwSrc, selectCtx); });
            var note = document.createElement("p");
            note.className = "to-a";
            note.textContent = "retrieval only \u2014 these passages are the answer; " +
              "nothing is composed on top. (engine v0)";
            rwSrc.appendChild(note);
            fillEngine("hit", c, top, resolveSpineMatch(question, "hit", c, top, null, null));
            setFollowup(pickFollowup(question, top[0], c));
            announce("sources found — retrieval only");
          }
        };
        // yield one frame so "reading N passages" can paint; not inserted latency
        requestAnimationFrame(go);
      }).catch(function () {
        status.remove();
        printAbstain("ENGINE_UNREACHABLE",
          "the korpus could not be loaded \u2014 no answer will be invented in its place.", rwSrc);
        fillEngine("abstain", null, []);
        setFollowup(pickFollowup(question, null, null));
        announce("ENGINE_UNREACHABLE");
      });
    });
  }

  /* ================= the world: the planet — altitude = abstraction =================
     orbit: whole ring, replay highlights each real event in time order.
     surface: visitor-controlled zoom down — labels become legible.
     detail (ground): one event with its receipt. The dark center is never entered. */
  var altState = { alt: "orbit" };
  (function () {
    var planet = document.getElementById("world-stage");
    var ring = document.getElementById("pl-ring");
    var field = document.getElementById("pl-field");
    if (!planet || !ring || !field) return;
    var evs = Array.prototype.slice.call(ring.querySelectorAll(".pl-ev"));
    var svs = Array.prototype.slice.call(document.querySelectorAll("#surface-list .sv-ev"));
    var nowLine = document.getElementById("pl-now");
    var detailEl = document.getElementById("pl-detail");
    var pdGlyph = document.getElementById("pd-glyph");
    var pdTitle = document.getElementById("pd-title");
    var pdSub = document.getElementById("pd-sub");
    var pdWhen = document.getElementById("pd-when");
    var ctls = document.getElementById("pl-ctls");
    var bDown = document.getElementById("pl-down");
    var bUp = document.getElementById("pl-up");
    var bPrev = document.getElementById("pl-prev");
    var bNext = document.getElementById("pl-next");
    var bPlay = document.getElementById("replay-ctl");
    var N = evs.length;
    var st = { i: N - 1, sel: N - 1, timer: null, userPaused: false, started: false };
    var defaultNow = nowLine.textContent;

    function data(i) {
      var li = svs[i];
      var l = li.querySelector(".l").textContent;
      var cut = l.indexOf(" — ");
      return {
        glyph: li.querySelector(".g").textContent,
        t: li.querySelector(".t").textContent,
        kind: (li.className.match(/k-\w+/) || ["k-commit"])[0],
        title: cut > 0 ? l.slice(0, cut) : l,
        sub: cut > 0 ? l.slice(cut + 3) : ""
      };
    }

    function highlight(i) {
      evs.forEach(function (e) { e.classList.remove("now"); });
      evs[i].classList.add("now");
      var d = data(i);
      nowLine.textContent = "now: " + d.glyph + " " + d.t + " · " + d.title +
        (d.sub ? " — " + d.sub : "");
    }

    function setOrigin(i) {
      var cs = getComputedStyle(evs[i]);
      var a = parseFloat(cs.getPropertyValue("--a")) * Math.PI / 180;
      var r = parseFloat(cs.getPropertyValue("--r"));
      var fw = field.clientWidth;
      var R = (fw - 60) / 2;
      var cx = fw / 2 + R * r * Math.cos(a);
      var cy = fw / 2 + R * r * Math.sin(a);
      ring.style.setProperty("--ox", cx.toFixed(1) + "px");
      ring.style.setProperty("--oy", cy.toFixed(1) + "px");
    }

    function showDetail(i) {
      var d = data(i);
      pdGlyph.textContent = d.glyph;
      pdGlyph.style.color = getComputedStyle(evs[i]).color;
      pdTitle.textContent = d.title + ".";
      pdSub.textContent = d.sub;
      pdWhen.textContent = d.t + " · event " + (i + 1) + " of " + N;
    }

    function posOf(el) {
      var cs = getComputedStyle(el);
      return { a: parseFloat(cs.getPropertyValue("--a")), r: parseFloat(cs.getPropertyValue("--r")) };
    }
    // tells the decorative orbiters canvas which two REAL events the replay just
    // moved between, so it can trace that exact hop — never a new claim, just a
    // nicer way to look at the same tick.
    function emitStep(prevIdx, curIdx) {
      if (altState.alt !== "orbit") return;
      field.dispatchEvent(new CustomEvent("world:tick", { detail: {
        from: posOf(evs[prevIdx]), to: posOf(evs[curIdx]), color: getComputedStyle(evs[curIdx]).color
      }}));
    }

    function stopReplay() { clearTimeout(st.timer); st.timer = null; }
    function tick() {
      var prevI = st.i;
      st.i = (st.i + 1) % N;
      st.sel = st.i;
      emitStep(prevI, st.i);
      highlight(st.i);
      st.timer = setTimeout(tick, st.i === N - 1 ? 3200 : 950);
    }
    function startReplay() {
      if (!motionOK() || st.timer) return;
      st.timer = setTimeout(tick, 400);
    }

    function setAlt(alt) {
      altState.alt = alt;
      planet.dataset.altitude = alt;
      detailEl.hidden = alt !== "detail";
      bDown.hidden = alt === "detail";
      bUp.hidden = alt === "orbit";
      bPrev.hidden = bNext.hidden = alt !== "detail";
      bPlay.hidden = alt !== "orbit" || !motionOK();
      if (alt === "orbit") {
        nowLine.textContent = defaultNow;
        evs.forEach(function (e) { e.classList.remove("now"); });
        if (!st.userPaused) startReplay();
      } else {
        stopReplay();
        setOrigin(st.sel);
        highlight(st.sel);
      }
      window.dispatchEvent(new Event("scroll")); // depth gauge echoes the altitude
    }

    ctls.hidden = false;
    bPlay.hidden = !motionOK();
    bDown.addEventListener("click", function () {
      setAlt(altState.alt === "orbit" ? "surface" : "detail");
      if (altState.alt === "detail") showDetail(st.sel);
    });
    bUp.addEventListener("click", function () {
      setAlt(altState.alt === "detail" ? "surface" : "orbit");
    });
    function step(d) {
      st.sel = (st.sel + d + N) % N;
      setOrigin(st.sel);
      highlight(st.sel);
      showDetail(st.sel);
    }
    bPrev.addEventListener("click", function () { step(-1); });
    bNext.addEventListener("click", function () { step(1); });
    bPlay.addEventListener("click", function () {
      st.userPaused = !st.userPaused;
      bPlay.textContent = st.userPaused ? "resume replay" : "pause replay";
      if (st.userPaused) stopReplay(); else startReplay();
    });
    evs.forEach(function (e, i) {
      e.addEventListener("click", function () {
        if (altState.alt !== "surface") return;
        st.sel = i;
        setOrigin(i);
        highlight(i);
        showDetail(i);
        setAlt("detail");
      });
    });

    if (motionOK() && "IntersectionObserver" in window) {
      var io = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting && !st.started) {
            st.started = true;
            startReplay();
            io.disconnect();
          }
        });
      }, { threshold: 0.35 });
      io.observe(field);
    }

    // OS preference flip mid-session: freeze to the static frame
    window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", function (m) {
      if (m.matches) {
        st.userPaused = true;
        stopReplay();
        bPlay.hidden = true;
      }
    });
  })();

  /* ================= planet: decorative orbiters (purely cosmetic — carries no data,
     unlike .pl-ev; never claims to be a recorded event) ================= */
  (function () {
    var canvas = document.getElementById("pl-orbiters");
    var field = document.getElementById("pl-field");
    if (!canvas || !field || !motionOK()) return;
    var ctx = canvas.getContext("2d");
    var dpr = Math.min(window.devicePixelRatio || 1, 2);

    function resize() {
      var r = field.getBoundingClientRect();
      canvas.width = r.width * dpr;
      canvas.height = r.height * dpr;
      canvas.style.width = r.width + "px";
      canvas.style.height = r.height + "px";
    }
    resize();
    window.addEventListener("resize", resize);

    function rand(a, b) { return a + Math.random() * (b - a); }

    var moons = [
      { radiusFrac: 0.92, speed: 0.045, phase: 0, size: 2.4, alpha: 0.65 },
      { radiusFrac: 1.04, speed: -0.028, phase: 2.1, size: 1.7, alpha: 0.45 },
      { radiusFrac: 0.80, speed: 0.07, phase: 4.2, size: 1.3, alpha: 0.5 }
    ];
    var streak = null; // occasional funny event: a small comet crossing the field

    // the replay's own comet: traces the exact hop between two REAL consecutive
    // events, colored by the kind it just landed on. Not a new fact — the same
    // tick the text already announces, just drawn as motion instead of a jump.
    var comet = null; // {x0,y0,x1,y1,start,dur,color}
    field.addEventListener("world:tick", function (e) {
      var d = e.detail;
      var w = canvas.width / dpr, h = canvas.height / dpr;
      var cx = w / 2, cy = h / 2, R = Math.min(w, h) / 2 - 6;
      function toXY(p) {
        var rad = p.a * Math.PI / 180;
        return { x: cx + Math.cos(rad) * R * p.r, y: cy + Math.sin(rad) * R * p.r };
      }
      var p0 = toXY(d.from), p1 = toXY(d.to);
      comet = { x0: p0.x, y0: p0.y, x1: p1.x, y1: p1.y, start: performance.now() / 1000, dur: 0.62, color: d.color };
    });

    function maybeSpawnStreak(tSec) {
      if (streak || Math.random() > 0.0006) return;
      var edge = Math.floor(rand(0, 4));
      var w = canvas.width / dpr, h = canvas.height / dpr;
      var pts = {
        0: [[-10, rand(0, h)], [w + 10, rand(0, h)]],
        1: [[w + 10, rand(0, h)], [-10, rand(0, h)]],
        2: [[rand(0, w), -10], [rand(0, w), h + 10]],
        3: [[rand(0, w), h + 10], [rand(0, w), -10]]
      }[edge];
      streak = { x0: pts[0][0], y0: pts[0][1], x1: pts[1][0], y1: pts[1][1], start: tSec, dur: rand(0.8, 1.4) };
    }

    var stopped = false;
    function draw(tMs) {
      if (stopped) return;
      requestAnimationFrame(draw);
      var tSec = tMs / 1000;
      var w = canvas.width / dpr, h = canvas.height / dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      var cx = w / 2, cy = h / 2;
      var R = Math.min(w, h) / 2 - 6;

      moons.forEach(function (m) {
        var a = tSec * m.speed + m.phase;
        var x = cx + Math.cos(a) * R * m.radiusFrac;
        var y = cy + Math.sin(a) * R * m.radiusFrac * 0.98;
        ctx.beginPath();
        ctx.arc(x, y, m.size, 0, Math.PI * 2);
        ctx.fillStyle = "rgba(216,178,74," + m.alpha + ")";
        ctx.fill();
      });

      if (comet) {
        var ct = (tSec - comet.start) / comet.dur;
        if (ct >= 1) {
          comet = null;
        } else {
          var ce = 1 - Math.pow(1 - ct, 3); // ease-out cubic — arrives with a settle, not a snap
          var hx = comet.x0 + (comet.x1 - comet.x0) * ce;
          var hy = comet.y0 + (comet.y1 - comet.y0) * ce;
          ctx.save();
          ctx.globalAlpha = 0.4 * (1 - ct);
          ctx.strokeStyle = comet.color;
          ctx.lineWidth = 1.3;
          ctx.beginPath();
          ctx.moveTo(comet.x0, comet.y0);
          ctx.lineTo(hx, hy);
          ctx.stroke();
          ctx.globalAlpha = 0.85 * (1 - ct * 0.3);
          ctx.beginPath();
          ctx.arc(hx, hy, 2.3, 0, Math.PI * 2);
          ctx.fillStyle = comet.color;
          ctx.fill();
          ctx.restore();
        }
      }

      maybeSpawnStreak(tSec);
      if (streak) {
        var lt = (tSec - streak.start) / streak.dur;
        if (lt >= 1) { streak = null; }
        else {
          var sx = streak.x0 + (streak.x1 - streak.x0) * lt;
          var sy = streak.y0 + (streak.y1 - streak.y0) * lt;
          var tailLen = 22;
          var dx = (streak.x1 - streak.x0) / Math.hypot(streak.x1 - streak.x0, streak.y1 - streak.y0);
          var dy = (streak.y1 - streak.y0) / Math.hypot(streak.x1 - streak.x0, streak.y1 - streak.y0);
          var grad = ctx.createLinearGradient(sx - dx * tailLen, sy - dy * tailLen, sx, sy);
          grad.addColorStop(0, "rgba(230,238,246,0)");
          grad.addColorStop(1, "rgba(230,238,246,0.85)");
          ctx.strokeStyle = grad;
          ctx.lineWidth = 1.3;
          ctx.beginPath();
          ctx.moveTo(sx - dx * tailLen, sy - dy * tailLen);
          ctx.lineTo(sx, sy);
          ctx.stroke();
        }
      }
    }
    // lazy start: don't spend a single frame on this decoration until the ring
    // is actually near the viewport — the terminal above shouldn't pay for it.
    if ("IntersectionObserver" in window) {
      var ioOrbiters = new IntersectionObserver(function (entries) {
        entries.forEach(function (entry) {
          if (entry.isIntersecting) {
            requestAnimationFrame(draw);
            ioOrbiters.disconnect();
          }
        });
      }, { threshold: 0.1 });
      ioOrbiters.observe(field);
    } else {
      requestAnimationFrame(draw);
    }

    window.matchMedia("(prefers-reduced-motion: reduce)").addEventListener("change", function (m) {
      if (m.matches) { stopped = true; comet = null; ctx.clearRect(0, 0, canvas.width, canvas.height); }
    });
  })();

  /* ================= crossing fixture (inside the boundary zoom) ================= */
  var crossing = document.getElementById("crossing");
  if (crossing && "IntersectionObserver" in window) {
    var cio = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          crossing.classList.add("crossing-armed");
          cio.disconnect();
        }
      });
    }, { threshold: 0.5 });
    cio.observe(crossing);
  } else if (crossing) {
    crossing.classList.add("crossing-armed");
  }

  /* ================= the void: the orbit of real events ================= */
  var blackhole = document.getElementById("blackhole");
  var orbitCtl = document.getElementById("orbit-ctl");
  if (blackhole && orbitCtl && motionOK()) {
    blackhole.classList.add("orbit-on");
    orbitCtl.hidden = false;
    orbitCtl.addEventListener("click", function () {
      var on = blackhole.classList.toggle("orbit-on");
      orbitCtl.textContent = on ? "pause the orbit" : "resume the orbit";
    });
  }

  /* ================= who-controls-it slider ================= */
  var range = document.getElementById("control-range");
  var readout = document.getElementById("control-readout");
  if (range && readout) {
    var states = [
      "unanswerable power",
      "power answerable to a boardroom",
      "answerable power. to you."
    ];
    var update = function () { readout.textContent = states[Number(range.value)] || states[0]; };
    range.addEventListener("input", update);
    update();
  }

  /* ================= depth gauge: an honest instrument ================= */
  var pct = document.getElementById("gauge-pct");
  var stratumLabel = document.getElementById("gauge-stratum");
  var sections = Array.prototype.slice.call(document.querySelectorAll(".stratum[id]"));
  var names = {
    terminal: "the terminal",
    shaft: "the descent",
    world: "the world",
    boundary: "the boundary",
    m1: "the unfinished question",
    m2: "the wager",
    m5: "the constitution",
    hidden: "the hidden thing",
    m6: "the zeros",
    instrument: "the first instrument",
    "void": "the void",
    water: "the water",
    invitation: "the casting",
    about: "what is this site",
    colophon: "instruments"
  };
  function onScroll() {
    var doc = document.documentElement;
    var max = doc.scrollHeight - window.innerHeight;
    var p = max > 0 ? Math.round((window.scrollY / max) * 100) : 0;
    if (pct) pct.textContent = p + "%";
    if (stratumLabel) {
      var mid = window.scrollY + window.innerHeight * 0.5;
      var current = "the terminal";
      var curId = "terminal";
      for (var i = 0; i < sections.length; i++) {
        if (sections[i].offsetTop <= mid) {
          curId = sections[i].id;
          current = names[curId] || curId;
        }
      }
      // the zoom is the visualization's own journey, wired with the descent
      if (curId === "world") current += " · " + altState.alt;
      if (curId === "terminal" && terminal && terminal.classList.contains("has-result")) {
        current = "the first wiring";
      }
      stratumLabel.textContent = current;
    }
  }
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  renderLiveStatus();
})();
