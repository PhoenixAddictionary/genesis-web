#!/usr/bin/env python3
"""Verify the well prototype v3 (terminal -> world) in headless Chrome via raw CDP
and capture screenshots + the journey recording into the project store."""

import base64
import json
import os
import re
import socket
import struct
import subprocess
import time
from pathlib import Path

import requests

DEBUG_PORT = 9222
URL = "http://localhost:8017/"
# read live, not hardcoded: a version-bump (korpus 0.3 -> 0.4 -> ...) must never
# silently desync this from the real corpus.json the suite is actually running
# against (found 2026-09-17: this used to be a hardcoded "0.3" string here).
KORPUS_VERSION = json.loads((Path(__file__).resolve().parent / "corpus.json").read_text(encoding="utf-8"))["version"]
# was a hardcoded absolute path into a specific Cursor cloud-agent's own
# working directory (bc-0987524e...) - worked by accident on the machine that
# happened to have that exact path writable, broke with PermissionError on
# every other machine (found running this in CI, 2026-09-17). Media belongs
# next to the script, not inside another tool's private state.
MEDIA = Path(__file__).resolve().parent / "media" / "well-prototype"
MEDIA.mkdir(parents=True, exist_ok=True)
FRAMES = Path("/tmp/well-frames")

checks = []


def check(name, ok, detail=""):
    checks.append((name, bool(ok), detail))
    print(("PASS  " if ok else "FAIL  ") + name + ("  -- " + str(detail) if detail else ""))


# ---------------- minimal websocket client ----------------
class WS:
    def __init__(self, url, timeout=120):
        rest = url[5:]
        hostport, _, path = rest.partition("/")
        host, _, port = hostport.partition(":")
        self.sock = socket.create_connection((host, int(port)), timeout=timeout)
        self.sock.settimeout(timeout)
        key = base64.b64encode(os.urandom(16)).decode()
        req = ("GET /" + path + " HTTP/1.1\r\nHost: " + hostport +
               "\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: " + key +
               "\r\nSec-WebSocket-Version: 13\r\n\r\n")
        self.sock.sendall(req.encode())
        resp = b""
        while b"\r\n\r\n" not in resp:
            chunk = self.sock.recv(4096)
            if not chunk:
                raise ConnectionError("handshake failed")
            resp += chunk
        if b" 101" not in resp.split(b"\r\n", 1)[0]:
            raise ConnectionError(resp.split(b"\r\n", 1)[0].decode(errors="replace"))
        _, _, rem = resp.partition(b"\r\n\r\n")
        self.buf = rem

    def _read(self, n):
        while len(self.buf) < n:
            chunk = self.sock.recv(1 << 18)
            if not chunk:
                raise ConnectionError("socket closed")
            self.buf += chunk
        out, self.buf = self.buf[:n], self.buf[n:]
        return out

    def _send_frame(self, opcode, payload):
        header = bytearray([0x80 | opcode])
        n = len(payload)
        if n < 126:
            header.append(0x80 | n)
        elif n < 65536:
            header.append(0x80 | 126)
            header += struct.pack(">H", n)
        else:
            header.append(0x80 | 127)
            header += struct.pack(">Q", n)
        mask = os.urandom(4)
        header += mask
        header += bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
        self.sock.sendall(bytes(header))

    def send(self, text):
        self._send_frame(0x1, text.encode())

    def recv(self):
        msg = b""
        while True:
            hdr = self._read(2)
            fin, opcode = hdr[0] & 0x80, hdr[0] & 0x0F
            n = hdr[1] & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            if hdr[1] & 0x80:
                mask = self._read(4)
                data = bytes(x ^ mask[i % 4] for i, x in enumerate(self._read(n)))
            else:
                data = self._read(n)
            if opcode == 0x9:
                self._send_frame(0xA, data)
                continue
            if opcode == 0x8:
                raise ConnectionError("closed by server")
            msg += data
            if fin:
                return msg.decode()


class Tab:
    def __init__(self):
        r = requests.put(f"http://127.0.0.1:{DEBUG_PORT}/json/new?about:blank")
        if r.status_code >= 400:
            r = requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/new?about:blank")
        self.info = r.json()
        self.ws = WS(self.info["webSocketDebuggerUrl"])
        self.msg_id = 0
        self.fire_and_forget = set()
        self.cmd("Network.enable")
        self.cmd("Network.setCacheDisabled", {"cacheDisabled": True})

    def _next(self):
        self.msg_id += 1
        return self.msg_id

    def send_nowait(self, method, params=None):
        i = self._next()
        self.fire_and_forget.add(i)
        self.ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
        return i

    def cmd(self, method, params=None):
        i = self._next()
        self.ws.send(json.dumps({"id": i, "method": method, "params": params or {}}))
        while True:
            m = json.loads(self.ws.recv())
            if m.get("id") == i:
                if "error" in m:
                    raise RuntimeError(f"{method}: {m['error']}")
                return m.get("result", {})
            self.fire_and_forget.discard(m.get("id"))

    def eval(self, expr, await_promise=False):
        r = self.cmd("Runtime.evaluate", {
            "expression": expr, "returnByValue": True, "awaitPromise": await_promise,
        })
        if "exceptionDetails" in r:
            raise RuntimeError(str(r["exceptionDetails"])[:300])
        return r["result"].get("value")

    def goto(self, url):
        self.cmd("Page.enable")
        self.cmd("Page.navigate", {"url": url})
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                if self.eval("document.readyState") == "complete":
                    time.sleep(0.5)
                    return
            except RuntimeError:
                pass
            time.sleep(0.3)
        raise TimeoutError("page load")

    def shot(self, path):
        r = self.cmd("Page.captureScreenshot", {"format": "png"})
        Path(path).write_bytes(base64.b64decode(r["data"]))
        print("saved", path)

    def outer_html(self):
        root = self.cmd("DOM.getDocument", {"depth": 0})["root"]["nodeId"]
        return self.cmd("DOM.getOuterHTML", {"nodeId": root})["outerHTML"]

    def close(self):
        try:
            requests.get(f"http://127.0.0.1:{DEBUG_PORT}/json/close/{self.info['id']}")
        except Exception:
            pass


# Was "who should a mind beyond ours answer to?" -- that question's own score
# dropped below the ANSWERED threshold once korpus grew past 0.3 (293 -> 358
# passages shifts BM25's corpus-wide IDF weights for every term, honestly, not
# a bug -- see well.js's solidnessRule). Replaced with a question anchored to
# a real, distinctive term ("Tadvana") added in that same growth, so it stays
# meaningfully verified against the ANSWERED code path rather than papering
# over the shift by loosening the assertions themselves.
ASK = "why is brahman called tadvana?"

SUBMIT_JS = """(() => {
  const i = document.getElementById('ask-input');
  i.value = %r;
  document.getElementById('ask-form').requestSubmit();
})()""" % ASK


def main():
    # ---------- 1. NORMAL ----------
    tab = Tab()
    errors = []
    tab.goto(URL)
    check("normal: title", "GENESIS" in tab.eval("document.title"))
    check("normal: JS active", tab.eval("document.documentElement.classList.contains('js')"))
    check("normal: seam fixed full-depth",
          tab.eval("getComputedStyle(document.querySelector('.seam')).position") == "fixed")
    check("normal: terminal is the first view",
          tab.eval("document.querySelector('.stratum').id") == "terminal")
    check("normal: fake caret visible pre-focus",
          tab.eval("getComputedStyle(document.querySelector('.term-caret')).display") == "block")
    check("normal: what-is-this exit on first screen",
          tab.eval("document.querySelector('.whatis').getAttribute('href')") == "#about")
    check("normal: message silence at terminal",
          "owner" not in str(tab.eval("document.getElementById('terminal').innerText")).lower())

    # pill fills the prompt
    check("normal: pill fills prompt", tab.eval("""(() => {
      const b = document.querySelector('.term-pills button.suggestion');
      if (!b) return false;
      b.click();
      return document.getElementById('ask-input').value === b.textContent;
    })()"""))
    tab.eval("document.getElementById('ask-input').value = ''")

    check("normal: first wiring hidden at rest",
          tab.eval("document.getElementById('result-windows').hidden"))

    # submit -> three windows pop over the empty terminal (the first wiring)
    # (first question also loads + indexes the corpus: allow for it)
    tab.eval(SUBMIT_JS)
    time.sleep(3.5)
    src_text = tab.eval("document.getElementById('rw-src-body').innerText")
    eng_text = tab.eval("document.getElementById('rw-eng-body').innerText")
    pic_text = tab.eval("document.getElementById('rw-pic-body').innerText")
    check("normal: question echoed in the wiring",
          ASK in tab.eval("document.getElementById('rw-q').innerText"))
    check("normal: three windows pop over the terminal",
          tab.eval("""(() => {
            const rw = document.getElementById('result-windows');
            return !rw.hidden
              && getComputedStyle(rw).display === 'grid'
              && document.querySelectorAll('.rw-pane').length === 3
              && document.getElementById('terminal').classList.contains('has-result');
          })()"""))
    check("normal: engine answers with real sources first",
          tab.eval("document.querySelectorAll('.to-src').length") >= 1
          and "sha256" in src_text)
    # Copy changed 2026-09-18 (Kimi visual thesis) from "retrieval only" to
    # "nothing was composed, nothing was kept" -- same honesty claim, clearer
    # wording; this check follows the meaning, not one frozen phrase.
    check("normal: no composed prose (retrieve mode)",
          "nothing was composed" in src_text or "NO_SOURCES" in src_text)
    check("normal: receipt binds korpus manifest", f"korpus {KORPUS_VERSION} manifest" in eng_text)
    check("normal: engine names good-for, driving, learning",
          "good for" in eng_text.lower()
          and "driving" in eng_text.lower()
          and "a first learning" in eng_text.lower()
          and "QUESTION_ANSWERED" in eng_text)

    # W4-3: "why this came up" -- each source's native <details> carries the
    # real matched terms + real BM25 score the retrieval already computed
    # (not a composed explanation, not a placeholder).
    check("normal: each source's 'why this came up' shows real matched terms + BM25 score",
          tab.eval("""(() => {
            const cards = [...document.querySelectorAll('#rw-src-body .to-src')];
            if (cards.length === 0) return false;
            return cards.every(c => {
              const why = c.querySelector('details.src-why');
              if (!why) return false;
              const body = why.textContent;
              const scoreOk = /BM25 score: -?\\d+\\.\\d{4}/.test(body);
              const termsOk = /matched terms: .+/.test(body)
                && !/matched terms: \\(no query term/.test(body);
              return scoreOk && termsOk;
            });
          })()"""))

    # W4-1: trace I -> II -- selecting a source in I re-points II's one
    # receipt line at that exact passage's id + full sha256.
    check("normal: selecting a source in I lights the exact receipt in II",
          tab.eval("""(() => {
            const card = document.querySelector('#rw-src-body .to-src');
            if (!card) return false;
            const sel = card.querySelector('.to-src-select');
            const wantId = card.dataset.passageId;
            const wantSha = card.dataset.passageSha256;
            if (!sel || !wantId || !wantSha) return false;
            sel.click();
            const rc = document.querySelector('#rw-eng-body .to-rcpt');
            // the receipt line truncates the hash the same way the rest of
            // the page does (renderSource, the base receiptLine) -- check
            // against that same 8-char prefix, not the full 64-char value.
            return card.classList.contains('to-src-selected')
              && sel.getAttribute('aria-pressed') === 'true'
              && !!rc && rc.textContent.includes(wantId) && rc.textContent.includes(wantSha.slice(0, 8));
          })()"""))
    n_ring_baseline = tab.eval("document.querySelectorAll('#pl-ring .pl-ev').length")
    check("normal: living picture peeks the real ring",
          tab.eval("document.querySelectorAll('.rw-dot').length") == n_ring_baseline
          and "stays off the ring" in pic_text.lower()
          and tab.eval("document.querySelector('.rw-peek-center').textContent.trim()") == "",
          f"ring={n_ring_baseline}")

    # W4-2: II -> III affordance -- one shared driving-state object, not two
    # hardcoded copies of "CONCEPT"/the fallback copy. Read the real shipped
    # well.js from disk (named witness: this exact file, next to this
    # script) rather than trusting a comment.
    well_js_src = (Path(__file__).parent / "well.js").read_text(encoding="utf-8")
    # Owner finding 2026-09-18: the old copy ("not on the ring yet") implied
    # every question eventually joins it. Replaced with copy that states the
    # real, permanent boundary (only 4 curated questions ever do) -- this
    # check now verifies THAT string has one source, not the retired one.
    not_on_ring_count = well_js_src.count("stays off the ring")
    check("normal: III's fallback copy has exactly one source in well.js (no hardcoded duplicate)",
          not_on_ring_count == 1, f"count={not_on_ring_count}")
    check("normal: fillEngine and fillPicture share one driving-state object (engineDriving)",
          well_js_src.count("engineDriving") >= 4)
    # GX-005 update: this branch was "guarded/unreachable" before spine.jsonl
    # existed (no real spine event anywhere in the project). It is reachable
    # now, for exactly the 4 curated questions in well.js's SPINE_QUESTION_MAP
    # -- proven live in the "SPINE WIRING" block below, not just grepped here.
    check("normal: a RECORDED branch exists for III, default state is still CONCEPT",
          'engineDriving.kind === "RECORDED"' in well_js_src
          and 'engineDriving = { kind: "CONCEPT"' in well_js_src
          and "SPINE_QUESTION_MAP" in well_js_src
          and "resolveSpineMatch" in well_js_src)
    check("normal: window II names the real korpus probe receipt (10/10, real manifest)",
          "10/10" in eng_text and "locators matched" in eng_text.lower()
          and "409032026696" in eng_text)

    # W4-4: one curated follow-up after a result -- never generated,
    # distinct from the three terminal pills, replaces rather than appends.
    followup_hidden = tab.eval("document.getElementById('rw-followup').hidden")
    followup_q = tab.eval("document.getElementById('rw-followup').dataset.question")
    check("normal: a curated follow-up appears after a result",
          (not followup_hidden) and bool(followup_q) and len(followup_q) > 5, followup_q)
    check("normal: the follow-up is distinct from the three terminal pills", followup_q not in [
          "why is the door of the true covered with a golden disk?",
          "should a ruler be loved or feared by the people?",
          "does the sage claim credit for what he produces?"], followup_q)
    tab.eval("document.getElementById('rw-followup').click()")
    time.sleep(1.5)
    check("normal: clicking the follow-up refills the terminal and re-answers with its exact question",
          followup_q in tab.eval("document.getElementById('rw-q').textContent")
          and tab.eval("document.getElementById('ask-input').value") == ""
          and (tab.eval("document.querySelectorAll('.to-src').length") >= 1
               or "NO_SOURCES" in tab.eval("document.getElementById('rw-src-body').innerText")),
          followup_q)
    check("normal: the follow-up replaces the result -- still exactly 3 panes, no thread",
          tab.eval("document.querySelectorAll('.rw-pane').length") == 3)

    check("normal: descent is offered, not forced",
          "enter the world" in tab.eval("document.getElementById('rw-enter').textContent").lower()
          and tab.eval("window.scrollY") == 0)
    check("normal: blessed prompt stays empty under the masks",
          tab.eval("getComputedStyle(document.querySelector('.term-center')).visibility") == "hidden")
    check("normal: depth gauge names the wiring",
          "first wiring" in tab.eval("document.getElementById('gauge-stratum').textContent"))

    # ask again restores the empty terminal
    tab.eval("document.getElementById('rw-again').click()")
    check("normal: ask-again also clears the follow-up suggestion",
          tab.eval("document.getElementById('rw-followup').hidden") is True)
    check("normal: ask-again restores the empty terminal",
          tab.eval("""(() => {
            return document.getElementById('result-windows').hidden
              && !document.getElementById('terminal').classList.contains('has-result')
              && getComputedStyle(document.querySelector('.term-center')).visibility !== 'hidden';
          })()"""))

    # ---------- PILL RETRIEVAL — the bug this session fixes ----------
    # The site's own 3 example pills (index.html .term-pills) used to be
    # "what crosses the seam?" / "who controls the most capable minds
    # today?" / "can a public thing stay un-owned?" -- verified NO_SOURCES
    # against the real engine (probes/korpus-0.3.json pill-1/2/3), so a
    # visitor's first click on the site's own suggested question landed on
    # "no sources found." Read the pill text live from the DOM (never
    # hardcoded here) so this check tracks whatever index.html actually
    # ships, not a remembered string.
    pill_texts = tab.eval(
        "[...document.querySelectorAll('.term-pills .suggestion')].map(el => el.textContent)")
    check("pills: exactly 3 example questions are offered", len(pill_texts) == 3, pill_texts)
    for pq in pill_texts:
        tab.eval("""(() => {
          const i = document.getElementById('ask-input');
          i.value = %r;
          document.getElementById('ask-form').requestSubmit();
        })()""" % pq)
        time.sleep(1.5)
        s = tab.eval("document.getElementById('rw-src-body').innerText")
        cards = tab.eval("""
          [...document.querySelectorAll('#rw-src-body .to-src')].map(d => ({
            id: d.dataset.passageId, sha: d.dataset.passageSha256
          }))
        """)
        check("pills: '" + pq + "' resolves ANSWERED with real sources, not NO_SOURCES",
              "NO_SOURCES" not in s and len(cards) >= 1
              and all(c["id"] and c["sha"] for c in cards),
              cards)
        tab.eval("document.getElementById('rw-again').click()")
        time.sleep(0.3)

    tab.eval(SUBMIT_JS)
    time.sleep(1.2)

    # a philosophical question genuinely lands
    tab.eval("""(() => {
      const i = document.getElementById('ask-input');
      i.value = 'what is emptiness?';
      document.getElementById('ask-form').requestSubmit();
    })()""")
    time.sleep(1.2)
    t2 = tab.eval("document.getElementById('rw-src-body').innerText")
    check("normal: 'what is emptiness?' lands in real passages",
          tab.eval("document.querySelectorAll('.to-src').length") >= 1
          and ("Tao" in t2 or "Upanishad" in t2 or "Ecclesiastes" in t2), t2[:90])

    # out-of-corpus -> typed abstention, never invention
    tab.eval("""(() => {
      const i = document.getElementById('ask-input');
      i.value = 'how do i configure a kubernetes ingress controller?';
      document.getElementById('ask-form').requestSubmit();
    })()""")
    time.sleep(1.0)
    t3 = tab.eval("document.getElementById('rw-src-body').innerText")
    e3 = tab.eval("document.getElementById('rw-eng-body').innerText")
    check("normal: out-of-corpus question gets typed abstention",
          "NO_SOURCES" in t3 and "QUESTION_ABSTAINED" in e3 and "korpus" in e3, t3[:90])

    # W4-5 CONTESTED (Owner ruling R2, 2026-09-16): a real, live-verified
    # pair -- Katha Upanishad 5.11-15 (the Self is eternal) vs Ecclesiastes
    # 12 (the dust returns to the earth, vanity of vanities). Outcome stays
    # ANSWERED with both positions labeled contested; never a CONTESTED
    # abstention, never a winner picked.
    # dots counted immediately BEFORE this submit, not a hardcoded 30 -- the
    # earlier follow-up-click test (above) happens to land on this exact
    # session's other curated question ("what happens to the soul after
    # death?", the FOLLOWUP_DEFAULT), which is itself spine-wired and may
    # already have added its own glyph. A relative delta is the only
    # assertion that stays true regardless of what ran earlier in this file.
    dots_before_contested = tab.eval("document.querySelectorAll('.rw-dot').length")
    tab.eval("""(() => {
      const i = document.getElementById('ask-input');
      i.value = 'is the self eternal or does it return to dust?';
      document.getElementById('ask-form').requestSubmit();
    })()""")
    time.sleep(1.5)
    src5 = tab.eval("document.getElementById('rw-src-body').innerText")
    eng5 = tab.eval("document.getElementById('rw-eng-body').innerText")
    pic5 = tab.eval("document.getElementById('rw-pic-body').innerText")
    contested_ids = tab.eval("""
      [...document.querySelectorAll('#rw-src-body .to-contested .to-src')]
        .map(el => el.dataset.passageId)
    """)
    check("normal: CONTESTED question shows exactly the two real sourced positions in I",
          contested_ids == ["upanishad:katha-upanishad-5-11-15", "kjv:ecclesiastes-12"],
          contested_ids)
    check("normal: CONTESTED labeling copy names both traditions plainly",
          "Katha Upanishad" in src5 and "Ecclesiastes" in src5, src5[:120])
    check("normal: CONTESTED stays ANSWERED (R2), not a CONTESTED abstention",
          "QUESTION_ANSWERED" in eng5 and "[CONTESTED]" not in src5
          and "contested" in eng5.lower())
    check("normal: CONTESTED never declares a winner",
          not re.search(r"\b\w+\s+wins\b|the winner is|correct answer is|true answer is", src5, re.I),
          src5[:200])
    # GX-005 update: this question is one of the 4 curated spine-wired
    # questions (spine/spine.jsonl, EVT-WELL-PROBE-CONTESTED-SELF-DUST-001).
    # The OLD invariant here ("still not on the ring, no glyph") was correct
    # for the pre-spine build and is now intentionally superseded by this
    # exact feature -- Window II must show RECORDED + the real eventId, and
    # exactly one new glyph must land on III's peek ring. Never lower this
    # to the old assertion again without re-checking spine/spine.jsonl.
    dots_after_contested = tab.eval("document.querySelectorAll('.rw-dot').length")
    check("normal: CONTESTED question is spine-wired -- II shows RECORDED + the real eventId",
          "RECORDED" in eng5 and "EVT-WELL-PROBE-CONTESTED-SELF-DUST-001" in eng5, eng5[-160:])
    check("normal: CONTESTED spine match adds exactly one new glyph to III's peek ring",
          dots_after_contested == dots_before_contested + 1,
          f"before={dots_before_contested} after={dots_after_contested}")
    check("normal: the new CONTESTED glyph is a distinct kind (k-question), not a baked commit/PR/CI glyph",
          tab.eval("document.querySelectorAll('.rw-dot.k-question').length") >= 1)
    check("normal: CONTESTED still offers a follow-up",
          not tab.eval("document.getElementById('rw-followup').hidden"))
    check("normal: selecting a contested card still traces I -> II (W4-1 unaffected)",
          tab.eval("""(() => {
            const card = document.querySelector('#rw-src-body .to-contested .to-src');
            if (!card) return false;
            card.querySelector('.to-src-select').click();
            const rc = document.querySelector('#rw-eng-body .to-rcpt');
            return !!rc && rc.textContent.includes('selected:');
          })()"""))

    # Owner fix 2026-09-17: the Owner looked at CONTESTED live and found an
    # inner scrollbar clipping Window I's text mid-sentence on a shorter
    # viewport. Fixed by dropping .rw.js-only's bottom pin and .rw-mask's
    # overflow:auto -- content now grows and the PAGE scrolls instead.
    # Prove it at realistic laptop heights where the old box genuinely
    # overflowed (measured before the fix: 1280x720 needed 580px, had 523;
    # 1024x768 needed 657px, had 571), on a throwaway tab so the main tab's
    # 1440x900 window (later checks assume it) is untouched.
    scroll_tab = Tab()
    scroll_tab.cmd("Emulation.setDeviceMetricsOverride", {
        "width": 1280, "height": 720, "deviceScaleFactor": 1, "mobile": False})
    scroll_tab.goto(URL)
    scroll_tab.eval("""(() => {
      const i = document.getElementById('ask-input');
      i.value = 'is the self eternal or does it return to dust?';
      document.getElementById('ask-form').requestSubmit();
    })()""")
    time.sleep(1.5)
    scroll_report = scroll_tab.eval("""
      [...document.querySelectorAll('.rw-mask')].map(m => ({
        cls: m.className, client: m.clientHeight, scroll: m.scrollHeight
      }))
    """)
    any_inner_scroll = any(m["scroll"] > m["client"] + 2 for m in scroll_report)
    check("normal: no inner scrollbar on any of the 3 window masks at 1280x720 (CONTESTED)",
          not any_inner_scroll, scroll_report)
    scroll_tab.cmd("Emulation.clearDeviceMetricsOverride")
    scroll_tab.close()

    # ---------- SPINE WIRING (GX-005) -- the actual point of this build ----------
    # spine/spine.jsonl maps exactly 4 curated questions to real, receipted
    # genesis.event.v1 records (see spine/README.md). Every other question --
    # the 3 pills, every other probe, any free text -- must keep showing
    # CONCEPT. Never remove or weaken any check below if this set is ever
    # extended; add new checks alongside them instead (spine/README.md
    # "Extending this set").
    def ask(q):
        tab.eval("""(() => {
          const i = document.getElementById('ask-input');
          i.value = %r;
          document.getElementById('ask-form').requestSubmit();
        })()""" % q)
        time.sleep(1.5)

    def dots():
        return tab.eval("document.querySelectorAll('.rw-dot').length")

    def eng_now():
        return tab.eval("document.getElementById('rw-eng-body').innerText")

    def pic_now():
        return tab.eval("document.getElementById('rw-pic-body').innerText")

    # 1) hit-tao-water -- ANSWERED, RECORDED, one new glyph
    d0 = dots()
    ask("what does the tao say about water?")
    e = eng_now()
    check("spine: 'what does the tao say about water?' shows RECORDED + the real eventId in II",
          "RECORDED" in e and "EVT-WELL-PROBE-HIT-TAO-WATER-001" in e, e[-160:])
    check("spine: the tao-water spine match adds exactly one new glyph to III",
          dots() == d0 + 1, f"before={d0} after={dots()}")
    # Owner finding 2026-09-18: the shaft's pull-back line made this exact
    # promise unconditionally for every question before any answer existed.
    # It's now driven by the same engineDriving state II/III already use --
    # verify it actually says something true for the one case it CAN be true.
    shaft = tab.eval("document.getElementById('shaft-hint').textContent")
    check("spine: shaft-hint confirms the real ring event for a RECORDED question",
          "one more real event on the ring" in shaft.lower(), shaft)

    # 2) hit-upanishad-soul-death -- this exact question was ALSO the curated
    # follow-up offered earlier in this run (FOLLOWUP_DEFAULT) and was
    # already clicked once above, so it may already have a glyph. Asking it
    # again must still show RECORDED (live re-verified on every submit) but
    # must NOT add a second glyph -- the event already "happened" once this
    # session, same real-world logic as a git/PR event never firing twice.
    d1 = dots()
    ask("what happens to the soul after death?")
    e = eng_now()
    check("spine: 'what happens to the soul after death?' shows RECORDED + the real eventId in II",
          "RECORDED" in e and "EVT-WELL-PROBE-HIT-UPANISHAD-SOUL-DEATH-001" in e, e[-160:])
    check("spine: asking an already-recorded question again does not duplicate its glyph",
          dots() == d1, f"before={d1} after={dots()}")

    # 3) no-match-kubernetes -- the EXACT mapped string ("...cluster?"),
    # deliberately distinct from the "...ingress controller?" wording used
    # earlier in this file (which is NOT in SPINE_QUESTION_MAP on purpose).
    # ABSTAINED, RECORDED, one new glyph.
    d2 = dots()
    ask("how do i configure a kubernetes cluster?")
    e = eng_now()
    s = tab.eval("document.getElementById('rw-src-body').innerText")
    check("spine: 'how do i configure a kubernetes cluster?' shows RECORDED + the real eventId in II",
          "RECORDED" in e and "EVT-WELL-PROBE-NO-MATCH-KUBERNETES-001" in e, e[-160:])
    check("spine: the kubernetes abstention stays a typed NO_SOURCES, never an invented answer",
          "NO_SOURCES" in s and "QUESTION_ABSTAINED" in e, s[:120])
    check("spine: the kubernetes spine match adds exactly one new glyph to III",
          dots() == d2 + 1, f"before={d2} after={dots()}")

    # repeat -- still no duplicate, from a fresh (non-follow-up) trigger path
    d3 = dots()
    ask("how do i configure a kubernetes cluster?")
    check("spine: repeating the kubernetes question again does not duplicate its glyph",
          dots() == d3, f"before={d3} after={dots()}")

    # 4) everything else -- the 3 real terminal pills, verbatim (now real,
    # solidly-retrieved questions post-fix -- see the PILL RETRIEVAL block
    # above; ANSWERED is not the same as RECORDED), plus one more unrelated
    # curated probe -- must keep showing CONCEPT and must NEVER grow the
    # glyph count. This is the negative-space half of the feature: only
    # these 4 exact strings (SPINE_QUESTION_MAP) are ever RECORDED.
    for q in ["why is the door of the true covered with a golden disk?",
              "should a ruler be loved or feared by the people?",
              "does the sage claim credit for what he produces?",
              "what's the best pizza topping?"]:
        d = dots()
        ask(q)
        p = pic_now()
        e = eng_now()
        if q == "why is the door of the true covered with a golden disk?":
            shaft = tab.eval("document.getElementById('shaft-hint').textContent")
            check("spine: shaft-hint stays honest for an unmapped (CONCEPT) question",
                  "stays concept, not recorded" in shaft.lower(), shaft)
        check("spine: unmapped question stays CONCEPT with no glyph -- " + repr(q),
              "stays off the ring" in p.lower() and "RECORDED" not in e and dots() == d,
              f"before={d} after={dots()}")

    # Owner ruling R1: labeled only by eventType, never by the question text.
    titles = tab.eval(
        "[...document.querySelectorAll('.rw-dot.k-question')].map(d => d.title)")
    check("spine: every spine glyph is labeled only by its eventType, never by question text",
          len(titles) > 0 and all(t in ("QUESTION_ANSWERED", "QUESTION_ABSTAINED") for t in titles),
          titles)

    # ---------- never on page load (a fresh tab, before any submit) ----------
    fresh_tab = Tab()
    fresh_tab.goto(URL)
    check("spine: zero .rw-dot glyphs exist on a fresh page load, before any question is asked",
          fresh_tab.eval("document.querySelectorAll('.rw-dot').length") == 0)
    fresh_tab.close()

    # user-initiated pull: click the offer in window III
    tab.eval("document.getElementById('rw-enter').click()")
    time.sleep(2.0)
    mid_y = tab.eval("window.scrollY")
    time.sleep(4.0)
    end_y = tab.eval("window.scrollY")
    world_y = tab.eval("document.getElementById('world').offsetTop")
    check("normal: pull moves the page", mid_y > 200, f"y@2s={mid_y}")
    check("normal: pull arrives at the world", abs(end_y - world_y) < 60,
          f"end={end_y} world={world_y}")

    # the planet: orbit replay, then the zoom journey (altitude = abstraction)
    time.sleep(3.0)
    check("normal: planet at orbit on arrival",
          tab.eval("document.getElementById('world-stage').dataset.altitude") == "orbit")
    n_ring = tab.eval("document.querySelectorAll('.pl-ev').length")
    check("normal: real events in the ring (count not pinned -- grows with real history)",
          n_ring > 0, f"n={n_ring}")
    check("normal: orbit replay highlighting one event",
          tab.eval("document.querySelectorAll('.pl-ev.now').length") == 1)
    check("normal: replay caption names a real event",
          "now:" in tab.eval("document.getElementById('pl-now').textContent"))
    check("normal: pause control works", tab.eval("""(() => {
      const b = document.getElementById('replay-ctl');
      b.click();
      const ok = b.textContent.includes('resume');
      b.click();
      return ok;
    })()"""))
    tab.eval("document.getElementById('pl-down').click()")
    time.sleep(1.4)
    check("normal: zoom down -> surface, labels legible",
          tab.eval("document.getElementById('world-stage').dataset.altitude") == "surface"
          and tab.eval("getComputedStyle(document.querySelector('.pl-lab')).display") == "block")
    tab.eval("document.getElementById('pl-down').click()")
    time.sleep(1.3)
    check("normal: zoom down -> ground: one event, receipted",
          tab.eval("document.getElementById('world-stage').dataset.altitude") == "detail"
          and not tab.eval("document.getElementById('pl-detail').hidden")
          and len(tab.eval("document.getElementById('pd-title').textContent")) > 3)
    check("normal: the void is never entered (center stays empty)",
          tab.eval("document.querySelector('.pl-center').textContent.trim()") == "")
    tab.eval("document.getElementById('pl-next').click()")
    check("normal: ground browsing works",
          "event" in tab.eval("document.getElementById('pd-when').textContent"))
    tab.eval("document.getElementById('pl-up').click()")
    time.sleep(0.3)
    tab.eval("document.getElementById('pl-up').click()")
    time.sleep(1.3)
    check("normal: zoom up returns to orbit",
          tab.eval("document.getElementById('world-stage').dataset.altitude") == "orbit")
    gauges_text = tab.eval("document.querySelector('.gauges-line').textContent")
    check("normal: gauges line true",
          f"{n_ring} EVENTS · 0 CROSSINGS" in gauges_text, gauges_text)
    check("normal: GX lane behind zoom", "GX-005 founding surface" in tab.eval(
        "document.getElementById('world').textContent"))

    check("normal: thunderbolt lands at m1",
          "owners do." in tab.eval("document.querySelector('.bolt').innerText").lower())
    check("normal: canon line at the water",
          "Minimal seeds. Maximum emergence." in tab.eval(
              "document.querySelector('.canon-line').textContent"))
    check("normal: all 4 chip kinds present", tab.eval(
        "['concept','recorded','current','rejected'].every(k => document.querySelector('.chip-'+k))"))
    check("normal: every chip explains its record", tab.eval(
        "[...document.querySelectorAll('.chip')].every(c => (c.title||'').includes('record'))"))
    n_zooms = tab.eval("document.querySelectorAll('details.zoom').length")
    check("normal: detail lives behind zoom-ins", n_zooms >= 12, f"zooms={n_zooms}")
    check("normal: hidden thing is its own beat (C2)", tab.eval(
        "document.getElementById('hidden').innerText").find("invisible by design") >= 0
        and tab.eval("!!document.querySelector('#hidden .absent-frame')"))
    n_void = tab.eval("document.querySelectorAll('.bh-ev').length")
    check("normal: void — real events in orbit, same count as the world ring, center renders nothing",
          n_void == n_ring
          and tab.eval("document.querySelector('.bh-void').textContent.trim()") == "",
          f"void={n_void} ring={n_ring}")
    check("normal: orbit is pausable", tab.eval("""(() => {
      const b = document.getElementById('orbit-ctl');
      if (b.hidden) return false;
      b.click();
      const off = !document.getElementById('blackhole').classList.contains('orbit-on');
      b.click();
      return off;
    })()"""))
    check("normal: no unresolved ruling placeholders",
          "NEEDS_RULING" not in tab.eval("document.body.innerText"))
    check("normal: role names never interactive (C1)", tab.eval(
        "[...document.querySelectorAll('a,button,input,summary')].every(el =>"
        " !/witness|passenger|null layer/i.test(el.textContent || ''))"))
    check("normal: scroll-driven progress line active", tab.eval(
        "getComputedStyle(document.querySelector('.descent-progress')).display") == "block")

    # ---------- screenshots (fresh tab for a pristine terminal) ----------
    tab.close()
    tab = Tab()
    tab.goto(URL)
    time.sleep(4.6)  # let the staged arrival settle
    tab.shot(MEDIA / "hero.png")
    tab.eval(SUBMIT_JS)
    time.sleep(3.2)
    tab.shot(MEDIA / "hero-question-entry.png")
    # the world: one still per altitude
    tab.eval("document.documentElement.style.scrollBehavior='auto';"
             "document.getElementById('world').scrollIntoView()")
    time.sleep(6.0)
    tab.shot(MEDIA / "mid-descent-seam-crossing.png")
    time.sleep(2.0)
    tab.shot(MEDIA / "zoom-orbit.png")
    tab.eval("document.getElementById('pl-down').click()")
    time.sleep(1.6)
    tab.shot(MEDIA / "zoom-surface.png")
    tab.eval("document.getElementById('pl-down').click()")
    time.sleep(1.5)
    tab.shot(MEDIA / "zoom-detail.png")
    tab.eval("document.getElementById('water').scrollIntoView({block:'center'})")
    time.sleep(0.6)
    tab.shot(MEDIA / "water.png")
    tab.close()

    # ---------- 2. NO-JS ----------
    tab = Tab()
    tab.cmd("Emulation.setScriptExecutionDisabled", {"value": True})
    tab.goto(URL)
    html = tab.outer_html()
    check("no-js: scripts did not run", 'class="js"' not in html.split(">", 1)[0])
    check("no-js: pills are plain text", 'button type="button" class="suggestion"' not in html
          and "why is the door of the true covered with a golden disk?" in html)
    check("no-js: form leads to the world", 'action="#world"' in html)
    check("no-js: first wiring stays JS-only",
          tab.eval("getComputedStyle(document.getElementById('result-windows')).display") == "none")
    n_html_ring = html.count('class="pl-ev')
    check("no-js: ring events + surface lines, same real count, no JS needed to see them",
          n_html_ring > 0 and html.count('class="sv-ev') == n_html_ring,
          f"ring={n_html_ring} surface={html.count('class=\"sv-ev')}")
    check("no-js: zoom controls absent (no dead buttons)", tab.eval(
        "getComputedStyle(document.getElementById('pl-ctls')).display") == "none")
    check("no-js: altitude frames exist as details",
          "zoom down — the surface" in html and "one event, in full" in html)
    check("no-js: state honesty on terminal",
          "engine v0 — retrieval only" in html and f"korpus {KORPUS_VERSION}" in html)
    check("no-js: thunderbolt readable", "Owners do." in html)
    check("no-js: canon line readable", "Minimal seeds. Maximum emergence." in html)
    tab.eval("document.documentElement.style.scrollBehavior='auto';"
             "document.getElementById('world').scrollIntoView()")
    time.sleep(0.5)
    tab.shot(MEDIA / "verify-nojs-world.png")
    tab.close()

    # ---------- 3. REDUCED MOTION ----------
    tab = Tab()
    tab.cmd("Emulation.setEmulatedMedia", {
        "features": [{"name": "prefers-reduced-motion", "value": "reduce"}]})
    tab.goto(URL)
    check("reduced: media query honored",
          tab.eval("matchMedia('(prefers-reduced-motion: reduce)').matches"))
    check("reduced: terminal static (no staged arrival)", tab.eval(
        "getComputedStyle(document.querySelector('.term-mark')).animationName") == "none")
    tab.eval(SUBMIT_JS)
    time.sleep(3.5)
    tab.eval("document.getElementById('rw-enter').click()")
    time.sleep(0.4)
    y = tab.eval("window.scrollY")
    world_y = tab.eval("document.getElementById('world').offsetTop")
    check("reduced: descent is an instant jump, no cinematic pull",
          abs(y - world_y) < 60, f"y={y} world={world_y}")
    time.sleep(1.0)
    check("reduced: orbit static, no replay, control hidden",
          tab.eval("document.querySelectorAll('.pl-ev.now').length") == 0
          and tab.eval("document.getElementById('replay-ctl').hidden"))
    check("reduced: zoom still works as instant frames", tab.eval("""(() => {
      document.getElementById('pl-down').click();
      return document.getElementById('world-stage').dataset.altitude === 'surface'
        && getComputedStyle(document.getElementById('pl-ring')).transitionDuration === '0s';
    })()"""))
    tab.eval("document.getElementById('pl-up').click()")
    check("reduced: scroll timeline fully detached", tab.eval(
        "getComputedStyle(document.querySelector('.descent-progress')).display") == "none"
        and tab.eval("getComputedStyle(document.querySelector('.bolt')).animationName") == "none")
    check("reduced: orbit static, control hidden", tab.eval(
        "getComputedStyle(document.querySelector('.bh-ring')).animationName") == "none"
        and tab.eval("document.getElementById('orbit-ctl').hidden"))
    tab.shot(MEDIA / "verify-reduced-motion-world.png")
    tab.close()

    # ---------- 4. RECORDINGS: the journey + the zoom + the working question ----------
    record_clip(JOURNEY_JS, "descent-v2.mp4", 200)
    record_clip(ZOOM_JS, "zoom-journey.mp4", 120)
    record_clip(QW_JS, "question-works.mp4", 120)

    failed = [c for c in checks if not c[1]]
    print(f"\n{len(checks) - len(failed)}/{len(checks)} checks passed")
    for name, _, d in failed:
        print("FAILED:", name, d)
    return 1 if failed else 0


JOURNEY_JS = """
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  await sleep(4800); // the first seconds of atmosphere
  const input = document.getElementById('ask-input');
  input.focus();
  for (const ch of %r) {
    input.value += ch;
    input.dispatchEvent(new Event('input'));
    await sleep(46);
  }
  await sleep(600);
  document.getElementById('ask-form').requestSubmit();
  await sleep(4200); // the three windows pop — first wiring (corpus also indexes)
  document.getElementById('rw-enter').click(); // the visitor chooses to enter the world
  await sleep(5400); // the pull + arrival
  await sleep(14000); // watch the world replay
  // continue the descent to the water
  document.documentElement.style.scrollBehavior = 'auto';
  const max = document.getElementById('water').offsetTop;
  let y = window.scrollY;
  while (y < max) {
    y = Math.min(y + 13, max);
    window.scrollTo(0, y);
    await sleep(16);
  }
  await sleep(3400);
  return 'done';
})()
""" % ASK


ZOOM_JS = """
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  document.documentElement.style.scrollBehavior = 'auto';
  document.getElementById('world').scrollIntoView();
  await sleep(6500);                              // orbit: watch the replay
  document.getElementById('pl-down').click();     // the visitor chooses to descend
  await sleep(3000);                              // surface: labels legible
  document.getElementById('pl-down').click();
  await sleep(3200);                              // ground: one event, receipted
  document.getElementById('pl-next').click();
  await sleep(2200);
  document.getElementById('pl-next').click();
  await sleep(2200);
  document.getElementById('pl-up').click();
  await sleep(2000);
  document.getElementById('pl-up').click();
  await sleep(2800);                              // back at orbit
  return 'done';
})()
"""


QW_JS = """
(async () => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const input = document.getElementById('ask-input');
  const type = async (s) => {
    input.focus();
    for (const ch of s) { input.value += ch; input.dispatchEvent(new Event('input')); await sleep(46); }
    await sleep(500);
    document.getElementById('ask-form').requestSubmit();
  };
  await sleep(4200);                                   // the blessed entry, at rest
  await type('what is emptiness?');
  await sleep(5600);                                   // three windows: sources / engine / living picture
  await type('who should a mind beyond ours answer to?');
  await sleep(5600);                                   // wiring updates in place — a different shelf
  await type('how do i configure a kubernetes ingress controller?');
  await sleep(5200);                                   // typed abstention: NO_SOURCES in window I
  return 'done';
})()
"""


def record_clip(expr, outname, min_frames):
    FRAMES.mkdir(exist_ok=True)
    for f in FRAMES.glob("*.jpg"):
        f.unlink()
    tab = Tab()
    tab.goto(URL)
    tab.cmd("Page.startScreencast", {
        "format": "jpeg", "quality": 78,
        "maxWidth": 1440, "maxHeight": 900, "everyNthFrame": 1,
    })
    eval_id = tab.send_nowait("Runtime.evaluate", {
        "expression": expr, "returnByValue": True, "awaitPromise": True,
    })
    tab.fire_and_forget.discard(eval_id)
    frames = []
    deadline = time.time() + 200
    while time.time() < deadline:
        m = json.loads(tab.ws.recv())
        if m.get("method") == "Page.screencastFrame":
            p = m["params"]
            fp = FRAMES / f"f{len(frames):05d}.jpg"
            fp.write_bytes(base64.b64decode(p["data"]))
            frames.append((fp, p["metadata"]["timestamp"]))
            tab.send_nowait("Page.screencastFrameAck", {"sessionId": p["sessionId"]})
        elif m.get("id") == eval_id:
            break
    tab.cmd("Page.stopScreencast")
    tab.close()
    check(f"recording {outname}: frames captured", len(frames) > min_frames,
          f"{len(frames)} frames")

    concat = FRAMES / "list.txt"
    lines = []
    for i, (fp, ts) in enumerate(frames):
        lines.append(f"file '{fp}'")
        dur = (frames[i + 1][1] - ts) if i + 1 < len(frames) else 0.6
        lines.append(f"duration {max(dur, 0.01):.4f}")
    lines.append(f"file '{frames[-1][0]}'")
    concat.write_text("\n".join(lines))
    out = MEDIA / outname
    # ffmpeg missing (e.g. this Windows box has none on PATH) used to crash
    # the whole run here with an uncaught FileNotFoundError, before this
    # check -- or the final tally -- ever ran. That silently discarded every
    # later check's result, which is worse than one honest FAIL. Catch it so
    # the check still fires (and fails truthfully) and the run continues.
    try:
        r = subprocess.run(
            ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat),
             "-fps_mode", "vfr", "-pix_fmt", "yuv420p",
             "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
             "-movflags", "+faststart", str(out)],
            capture_output=True, text=True)
        ok = r.returncode == 0 and out.exists()
        detail = r.stderr[-300:] if r.returncode else str(out)
    except FileNotFoundError as e:
        ok = False
        detail = f"ffmpeg not found on PATH: {e}"
    check(f"recording {outname}: encoded", ok, detail)


if __name__ == "__main__":
    raise SystemExit(main())
