"use strict";

const state = { replay: null, caseIndex: 0, mode: "ALL" };
const $ = (id) => document.getElementById(id);

function text(id, value) { $(id).textContent = value ?? "Unknown"; }

function renderReceipt(run) {
  const request = run.proofRequest;
  const receipt = run.attestation;
  text("receipt-heading", receipt.attestationId);
  text("result", receipt.result.verdict);
  text("who", `${receipt.observedSubject.agentId} · ${receipt.observedSubject.version} · ${receipt.observedSubject.runtime}`);
  text("delegation", `${request.delegation.scope.join(" · ")} until ${request.delegation.expiresAt}`);
  text("asked", request.requestedProof.task);
  text("observed", `${receipt.observation.method} · ${receipt.observation.protocol} · ${receipt.observation.environment}`);
  text("result-detail", `${receipt.result.actual.join(" ")} Unknown beyond this task, environment, version and time window.`);
  text("verified", `${receipt.evaluator.id} · ${receipt.evaluator.independence} · outcome fee: ${receipt.evaluator.paidOnOutcome ? "yes" : "no"}`);
  text("decided", `${receipt.authorization.owner}: ${receipt.authorization.decision}. No access token was created.`);
}

function renderTrace(run) {
  const visible = state.replay.canonicalEventTrace.filter((event) =>
    event.caseId === run.caseId && (state.mode === "ALL" || event.facets.includes(state.mode))
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
  text("trace-hash", `trace ${state.replay.canonicalEventTraceSha256}`);
  text("seed-state", state.replay.institutionSeed.state);
  text("seed-copy", state.replay.institutionSeed.observedPattern);
}

function initialize(replay) {
  state.replay = replay;
  const select = $("case-select");
  replay.cases.forEach((run, index) => {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = `${run.caseId} — ${run.attestation.result.verdict}`;
    select.append(option);
  });
  select.addEventListener("change", () => { state.caseIndex = Number(select.value); render(); });
  document.querySelectorAll(".mode").forEach((button) => button.addEventListener("click", () => {
    state.mode = button.dataset.mode;
    document.querySelectorAll(".mode").forEach((candidate) => {
      const selected = candidate === button;
      candidate.classList.toggle("active", selected);
      candidate.setAttribute("aria-pressed", String(selected));
    });
    renderTrace(state.replay.cases[state.caseIndex]);
  }));
  render();
}

fetch("replay.v1.json", { cache: "no-store" })
  .then((response) => {
    if (!response.ok) throw new Error(`Replay unavailable (${response.status})`);
    return response.json();
  })
  .then(initialize)
  .catch((error) => {
    text("receipt-heading", "Replay unavailable");
    text("result", "UNKNOWN");
    text("result-detail", `${error.message}. No result, authority or activity is inferred.`);
  });
