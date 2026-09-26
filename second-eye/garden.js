"use strict";

const state = { replay: null, caseIndex: 0, mode: "ALL", source: "observed:OBSERVED-001", observedMeta: null };
const $ = (id) => document.getElementById(id);

function text(id, value) { const el = $(id); if (el) el.textContent = value ?? "Unknown"; }

function claimClassOf(run, replay) {
  return run?.claimClass || run?.attestation?.claimClass || replay?.claimClass || "UNKNOWN";
}

function setWatermarkClass(cc) {
  const el = $("claim-watermark");
  if (!el) return;
  el.classList.toggle("watermark-observed", cc === "OBSERVED");
  el.classList.toggle("watermark-simulated", cc === "SIMULATED_NOT_OBSERVED");
  el.classList.toggle("watermark-unknown", cc === "UNKNOWN" || !cc);
}

function setResultClass(verdict) {
  const el = $("result");
  if (!el) return;
  el.classList.toggle("result-pass", verdict === "PASS");
  el.classList.toggle("result-fail", /FAIL|BLOCK|REFUSE|REVOKE/i.test(String(verdict || "")));
}

function renderLimitations(run) {
  const list = $("limitation-list");
  if (!list) return;
  const limits = run?.attestation?.limitations || [];
  list.replaceChildren(...limits.map((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    return li;
  }));
}

function renderDigests(run) {
  const obs = run?.attestation?.observation || {};
  text("input-digest", obs.inputDigest || "—");
  text("output-digest", obs.outputDigest || "—");
  if (state.source === "synthetic") {
    text("digest-match", "n/a for synthetic toy (SIMULATED_NOT_OBSERVED)");
    return;
  }
  const meta = state.observedMeta?.digestSelfCheck;
  if (!meta) {
    text("digest-match", "open observed bundle to compare evidence files");
    return;
  }
  const okIn = meta.inputDigest && meta.inputDigest === obs.inputDigest;
  const okOut = meta.outputDigest && meta.outputDigest === obs.outputDigest;
  text("digest-match", (okIn && okOut)
    ? "PASS — page digests match bundle digestSelfCheck / evidence hashes"
    : "FAIL — digests do not match bundle self-check");
}

function renderReceipt(run) {
  const request = run.proofRequest;
  const receipt = run.attestation;
  const cc = claimClassOf(run, state.replay);
  text("receipt-heading", receipt.attestationId);
  text("result", receipt.result.verdict);
  setResultClass(receipt.result.verdict);
  text("claim-class", cc);
  text("claim-watermark", cc);
  setWatermarkClass(cc);
  text("who", `${receipt.observedSubject.agentId} · ${receipt.observedSubject.version} · ${receipt.observedSubject.runtime}`);
  text("delegation", `${request.delegation.scope.join(" · ")} until ${request.delegation.expiresAt}`);
  text("asked", request.requestedProof.task);
  text("observed", `${receipt.observation.method} · ${receipt.observation.protocol} · ${receipt.observation.environment}`);
  text("result-detail", `${receipt.result.actual.join(" ")} Unknown beyond this task, environment, version and time window.`);
  text("verified", `${receipt.evaluator.id} · ${receipt.evaluator.independence} · outcome fee: ${receipt.evaluator.paidOnOutcome ? "yes" : "no"}`);
  const token = receipt.authorization?.accessToken;
  text("decided", `${receipt.authorization.owner}: ${receipt.authorization.decision}. Access token: ${token ? "PRESENT (invalid for Second Eye grant)" : "none"}. No Second Eye access grant. Rely or not is decided outside this receipt.`);
  renderLimitations(run);
  renderDigests(run);
}

function renderTrace(run) {
  const trace = state.replay.canonicalEventTrace || [];
  const visible = trace.filter((event) =>
    event.caseId === run.caseId && (state.mode === "ALL" || (event.facets || []).includes(state.mode))
  );
  $("trace").replaceChildren(...visible.map((event) => {
    const item = document.createElement("li");
    if (/FAILED|BLOCKED|REFUSED|REVOKED/.test(event.kind)) item.className = "adverse";
    const tick = document.createElement("span"); tick.className = "tick"; tick.textContent = `T+${event.tick}`;
    const kind = document.createElement("span"); kind.className = "kind"; kind.textContent = event.kind.replaceAll("_", " ");
    const summary = document.createElement("span"); summary.className = "summary"; summary.textContent = event.summary;
    item.append(tick, kind, summary);
    return item;
  }));
}

function render() {
  const run = state.replay.cases[state.caseIndex];
  renderReceipt(run);
  renderTrace(run);
  text("trace-hash", `trace ${state.replay.canonicalEventTraceSha256 || "—"}`);
  const seed = state.replay.institutionSeed || {};
  text("seed-state", seed.state || "CANDIDATE_ONLY");
  text("seed-copy", seed.observedPattern || "Repeated demand can emit a candidate seed. It cannot install authority.");
}

function bindCaseSelect(replay) {
  const select = $("case-select");
  select.replaceChildren();
  replay.cases.forEach((run, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${run.caseId} · ${run.attestation.result.verdict} · ${claimClassOf(run, replay)}`;
    select.append(option);
  });
  select.onchange = () => { state.caseIndex = Number(select.value); render(); };
}

function bindModes() {
  document.querySelectorAll(".mode").forEach((button) => button.addEventListener("click", () => {
    state.mode = button.dataset.mode;
    document.querySelectorAll(".mode").forEach((candidate) => {
      const selected = candidate === button;
      candidate.classList.toggle("active", selected);
      candidate.setAttribute("aria-pressed", String(selected));
    });
    renderTrace(state.replay.cases[state.caseIndex]);
  }));
}

function initialize(replay) {
  state.replay = replay;
  state.caseIndex = 0;
  bindCaseSelect(replay);
  render();
}

function loadSynthetic() {
  state.source = "synthetic";
  state.observedMeta = null;
  return fetch("replay.v1.json", { cache: "no-store" })
    .then((response) => {
      if (!response.ok) throw new Error(`Synthetic replay unavailable (${response.status})`);
      return response.json();
    })
    .then(initialize);
}

function loadObserved(id) {
  state.source = `observed:${id}`;
  const replayUrl = `observed/${id}/replay.v1.json`;
  const bundleUrl = `observed/${id}/bundle.json`;
  return Promise.all([
    fetch(replayUrl, { cache: "no-store" }).then((r) => {
      if (!r.ok) throw new Error(`Observed replay unavailable (${r.status})`);
      return r.json();
    }),
    fetch(bundleUrl, { cache: "no-store" }).then((r) => r.ok ? r.json() : null),
  ]).then(([replay, bundle]) => {
    state.observedMeta = bundle;
    initialize(replay);
  });
}

function syncUrl(value) {
  const url = new URL(location.href);
  if (value.startsWith("observed:")) {
    url.searchParams.set("source", "observed");
    url.searchParams.set("id", value.split(":")[1]);
  } else {
    url.searchParams.delete("source");
    url.searchParams.delete("id");
    url.searchParams.set("demo", "synthetic");
  }
  history.replaceState({}, "", url);
}

function applySource(value) {
  const select = $("source-select");
  if (select && select.value !== value) select.value = value;
  syncUrl(value);
  const loader = value.startsWith("observed:")
    ? loadObserved(value.split(":")[1])
    : loadSynthetic();
  return loader.catch((error) => {
    text("receipt-heading", "Replay unavailable");
    text("result", "UNKNOWN");
    setResultClass("UNKNOWN");
    text("claim-class", "UNKNOWN");
    text("claim-watermark", "UNKNOWN");
    setWatermarkClass("UNKNOWN");
    text("result-detail", `${error.message}. No result, authority or activity is inferred.`);
  });
}

function boot() {
  bindModes();
  const params = new URLSearchParams(location.search);
  const sourceParam = params.get("source");
  const idParam = params.get("id") || "OBSERVED-001";
  const demoParam = params.get("demo");
  const select = $("source-select");
  // Default = OBSERVED-001 (try-one hero). Synthetic only if explicitly requested.
  let initial = `observed:${idParam}`;
  if (sourceParam === "synthetic" || demoParam === "synthetic") initial = "synthetic";
  else if (sourceParam === "observed") initial = `observed:${idParam}`;
  else if (!sourceParam && !demoParam) initial = "observed:OBSERVED-001";

  if (select) {
    select.value = initial;
    select.addEventListener("change", () => applySource(select.value));
  }

  const synthBtn = $("btn-synthetic");
  if (synthBtn) {
    synthBtn.addEventListener("click", () => applySource("synthetic"));
  }

  applySource(initial);
}

boot();
