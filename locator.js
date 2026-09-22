/* locator.js — deterministic source-address resolution for the Well (I-103).

   Why this exists: Reciprocal Passage Stage 1 asked the Well about Genesis 1-3
   and got NO_SOURCES, even though all three chapters are admitted and indexed.
   Root cause (RECIPROCAL_PASSAGE_STAGE1_INSTRUMENT_DIAGNOSIS_2026-09-22.md):
   "Genesis 1-3" was treated as ordinary free-text vocabulary, so the explicit
   source address competed lexically against 358 passages and lost the
   matched-token floor (needed 9, best Genesis passage matched 5).

   What this module does: it separates SOURCE_SCOPE from ANALYTIC_LENS *before*
   retrieval, exactly as that diagnosis proposed -- and nothing else. It resolves
   an address to the passages the corpus itself publishes under that address. It
   composes nothing, ranks nothing, interprets nothing, and never lowers the
   lexical engine's abstention floors: a question with no recognised address is
   not this module's business and falls through to well.js untouched.

   Two rules carry most of the design:

   1. A bare work name is NOT an address. "…according to genesis?" stays a
      lexical question and keeps its frozen NO_SOURCES outcome (see
      probes/korpus-0.3.json, probeId near-miss-genesis). An address needs a
      work name AND a number.

   2. Every address this module knows is derived from the `loc` fields of the
      admitted corpus at load time. There is deliberately no hardcoded book
      list: a second list of the same names, maintained separately, is a list
      that drifts silently from the one that matters.

   No network, no storage, no logging, no telemetry: the module is a pure
   function over the corpus it is handed. */
(function (root, factory) {
  "use strict";
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.GenesisLocator = factory();
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /* The Well renders at most three sources. A locator that addressed twelve
     passages and showed three would be selecting on the reader's behalf --
     that is the interpretation this module exists to refuse. Above the cap it
     abstains and names the narrower address instead. */
  var MAX_ADDRESSED = 3;

  /* en dash, em dash, minus and friends all mean "-" in an address. */
  function normalize(s) {
    return String(s)
      .replace(/[‐-―−]/g, "-")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }

  /* "Bhagavad Gita 13.4 (2)" -> work "bhagavad gita", tail "13.4", dis "2".
     The (k) suffix is a corpus-internal disambiguator for two passages that
     share one address; it is not part of the address a reader can type, so
     siblings resolve together. */
  var LOC_RE = /^(.*?)\s+(\d[\d.\-]*)(?:\s+\((\d+)\))?$/;

  function splitLoc(loc) {
    var m = LOC_RE.exec(normalize(loc));
    if (!m) return null;
    return { work: m[1], tail: m[2], dis: m[3] || null };
  }

  /* An index over what the corpus actually publishes. Everything downstream
     reads from here, so an address can never outrun the admitted bytes. */
  function buildIndex(corpus) {
    var works = {};       // work name -> { tails: {tail: [i]}, order: [tail] }
    var unaddressable = []; // passages whose loc has no numeric tail
    (corpus.passages || []).forEach(function (p, i) {
      var parts = splitLoc(p.loc);
      if (!parts) { unaddressable.push(i); return; }
      var w = works[parts.work] || (works[parts.work] = { tails: {}, order: [] });
      if (!w.tails[parts.tail]) { w.tails[parts.tail] = []; w.order.push(parts.tail); }
      w.tails[parts.tail].push(i);
    });
    return { works: works, workNames: Object.keys(works).sort(), unaddressable: unaddressable };
  }

  /* Does number tail `tail` begin with chapter `n` as a whole number?
     "72" starts with "72" but not with "7" -- after "7" comes "2", not a
     separator. "1-5" starts with "1". "13.4" starts with "13", not "1". */
  function tailStartsWithChapter(tail, n) {
    if (tail === n) return true;
    if (tail.slice(0, n.length) !== n) return false;
    var next = tail.charAt(n.length);
    return next === "." || next === "-";
  }

  /* Find the work name that a query refers to just before a number.

     `phrase` is the raw run of words preceding the number. An exact work name
     wins. Otherwise a trailing-word suffix is accepted only when it belongs to
     exactly one work ("gita 2.2"); when it fits several ("upanishad 1.1") the
     reference is genuinely ambiguous and this returns the candidates rather
     than picking one. */
  function matchWork(index, phrase) {
    var words = normalize(phrase).split(" ").filter(Boolean);
    /* Walk from the longest trailing phrase inwards, so "what does genesis"
       yields the work "genesis" and not the sentence that carried it. The
       matched phrase is returned as well: an ambiguous reference has to be
       quoted back to the reader in the words they actually used. */
    for (var start = 0; start < words.length; start++) {
      var candidate = words.slice(start).join(" ");
      if (!candidate) continue;
      if (index.works[candidate]) return { work: candidate, phrase: candidate, candidates: [candidate] };
      var suffixOf = index.workNames.filter(function (w) {
        return w === candidate || w.endsWith(" " + candidate);
      });
      if (suffixOf.length === 1) return { work: suffixOf[0], phrase: candidate, candidates: suffixOf };
      if (suffixOf.length > 1) return { work: null, phrase: candidate, candidates: suffixOf };
    }
    return null;
  }

  /* Pull an address out of a question. Returns null when the question carries
     no address at all -- the ordinary case, which well.js handles lexically.

     Matches the LAST address-shaped run in the question, so "what does genesis
     1 say" and "read genesis 1" behave the same. */
  var ADDR_RE = /([a-z][a-z ]*?)\s+(\d[\d.]*)(?:\s*-\s*(\d[\d.]*))?/g;

  function parse(index, question) {
    var q = normalize(question);
    var best = null, m;
    ADDR_RE.lastIndex = 0;
    while ((m = ADDR_RE.exec(q)) !== null) {
      var hit = matchWork(index, m[1]);
      if (!hit) continue;
      var numbers = m[2] + (m[3] ? "-" + m[3] : "");
      best = {
        work: hit.work,
        candidates: hit.candidates,
        from: m[2],
        to: m[3] || null,
        /* The lens is read from what is left once the ADDRESS is removed, so
           the span covers the work phrase the reader actually typed -- not the
           canonical name it resolved to, which may be longer ("gita" ->
           "bhagavad gita") and was never in the sentence. */
        span: [m.index + (m[1].length - hit.phrase.length), m.index + m[0].length],
        /* What to quote back. The canonical work name when it is known, so the
           reader sees which address was actually read; their own words when it
           is ambiguous, so the question they asked is the one answered. */
        raw: (hit.work || hit.phrase) + " " + numbers
      };
    }
    return best;
  }

  /* Words that only carry the shape of a request ("what does X SAY ABOUT Y"),
     not its subject. The Well's own stopword list deliberately does not hold
     them, because it feeds the BM25 index and changing it would move every
     score in the korpus. This list is display-only and touches nothing that
     scores: it exists so the unanswered half is reported as "light" rather
     than "say, about, light". */
  var SCAFFOLDING = {};
  ("about say says said saying tell tells read reads show shows give gives " +
   "according please explain").split(" ").forEach(function (w) { SCAFFOLDING[w] = 1; });

  /* Whatever the question asks beyond the address. The Well may hand over the
     addressed source, but it must never imply it answered this part. */
  function lensOf(question, addr, tokenize) {
    if (!addr) return [];
    var q = normalize(question);
    var rest = q.slice(0, addr.span[0]) + " " + q.slice(addr.span[1]);
    return tokenize(rest, false).filter(function (t) { return !SCAFFOLDING[t]; });
  }

  function addressesOf(index, work) {
    var w = index.works[work];
    return w ? w.order.slice() : [];
  }

  function collect(index, work, chapter) {
    var w = index.works[work], out = [];
    if (!w) return out;
    if (w.tails[chapter]) out = out.concat(w.tails[chapter]);          // exact address
    else {
      w.order.forEach(function (tail) {                                 // chapter prefix
        if (tailStartsWithChapter(tail, chapter)) out = out.concat(w.tails[tail]);
      });
    }
    return out;
  }

  /* Resolve a parsed address against the corpus.

     Outcomes are all typed and all deterministic. None of them is a placeholder
     record: an address that resolves to nothing produces a refusal to render,
     never an empty passage. */
  function resolve(index, addr) {
    if (!addr) return null;
    if (!addr.work) {
      return { outcome: "LOCATOR_AMBIGUOUS_WORK", candidates: addr.candidates, addr: addr };
    }

    var chapters = [addr.from];
    if (addr.to) {
      var a = parseInt(addr.from, 10), b = parseInt(addr.to, 10);
      /* A range only expands when both ends are plain whole chapters and run
         forwards. "isha upanishad 1-5" is not a range here -- it is one exact
         address, and the exact match below catches it first. */
      var plain = /^\d+$/.test(addr.from) && /^\d+$/.test(addr.to);
      var exact = index.works[addr.work] && index.works[addr.work].tails[addr.from + "-" + addr.to];
      if (exact) chapters = [addr.from + "-" + addr.to];
      else if (plain && b >= a) {
        chapters = [];
        for (var n = a; n <= b; n++) chapters.push(String(n));
      }
    }

    var seen = {}, idxs = [];
    chapters.forEach(function (ch) {
      collect(index, addr.work, ch).forEach(function (i) {
        if (!seen[i]) { seen[i] = 1; idxs.push(i); }
      });
    });
    idxs.sort(function (x, y) { return x - y; });

    if (idxs.length === 0) {
      return {
        outcome: "LOCATOR_NOT_IN_CORPUS", addr: addr, work: addr.work,
        available: addressesOf(index, addr.work)
      };
    }
    if (idxs.length > MAX_ADDRESSED) {
      return {
        outcome: "LOCATOR_TOO_BROAD", addr: addr, work: addr.work,
        count: idxs.length, limit: MAX_ADDRESSED,
        available: addressesOf(index, addr.work)
      };
    }
    return { outcome: "LOCATOR_HIT", addr: addr, work: addr.work, indices: idxs };
  }

  return {
    MAX_ADDRESSED: MAX_ADDRESSED,
    normalize: normalize,
    splitLoc: splitLoc,
    buildIndex: buildIndex,
    parse: parse,
    resolve: resolve,
    lensOf: lensOf,
    addressesOf: addressesOf,
    _tailStartsWithChapter: tailStartsWithChapter
  };
});
