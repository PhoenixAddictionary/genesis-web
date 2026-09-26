# Second Eye — Außenperson / Outside person (Akzeptanz 4–5)

**Ziel / Goal:** Eine veröffentlichte Quittung prüfen und dem Owner **rely / not-rely** melden.  
Kein Konto, keine Zertifizierung, kein Zugang (`no grant`).

Chair A: `claimClass` ist `OBSERVED` **oder** `SIMULATED_NOT_OBSERVED`. Das Spielzeug (synthetic) bleibt simuliert.

**Live basis (2026-09-26):** `https://openpassage.org/second-eye/` (prod; tip `1a9d533`).  
Owner-Inbox für Schritt 5: `memoria-recovery@agentmail.to`

---

## Fünf Schritte (frozen)

### 1. Synthetisches Spielzeug öffnen
URL: **`https://openpassage.org/second-eye/`**  
(ohne Query = synthetic)

**Prüfen:** Wasserzeichen / watermark oben = **`SIMULATED_NOT_OBSERVED`**.  
claimClass-Zeile gleich. Digest-Match darf „n/a for synthetic toy“ sagen.

### 2. Beobachtete Quittung öffnen
URL: **`https://openpassage.org/second-eye/?source=observed&id=OBSERVED-001`**

**Prüfen:** Wasserzeichen = **`OBSERVED`**.  
Nicht mit Schritt 1 verwechseln.

### 3. Digests prüfen
Auf der OBSERVED-Seite, Panel **Digest check**:

| Feld | Erwarteter Wert (dry-run OBSERVED-001) |
|------|----------------------------------------|
| inputDigest | `669e6f15fca02e627a59c638ccfef8b832e6f33b1676acece7a32b369a69dded` |
| outputDigest | `c1f05788f462ea96c2186b70e63188231fe9cd4979826d79ad5221121e19f4cb` |
| local evidence match | muss lokal/staging die Evidence-Hashes bestätigen (nicht „n/a“) |

### 4. Limitations + kein Grant
Immer sichtbar unter **Limitations**:

- `NOT_GENERAL_QUALITY`
- `NOT_GENERAL_SAFETY`
- `NOT_LEGITIMACY`
- `NOT_COMPANY_AUTHORIZATION`
- `NOT_RECOGNIZED_CERTIFICATION`

**Zusätzlich:** Zeile „Decided by outside receipt“ / Access token = **none** (oder explizit *not* a Second Eye grant).  
Second Eye vergibt **keinen** Zugang.

### 5. Rely / not-rely an Owner
Eine kurze Antwort an den **Owner-Posteingang** (Kanal unten):

- Würden Sie **diese eine Aktion** auf dieser Quittung stützen? (**rely** / **not-rely**)
- Was fehlt?

**Owner inbox (channel):** `memoria-recovery@agentmail.to`  
Shared AgentMail inbox (also Memoria Discord recovery). Subject line example: `Second Eye OBSERVED-001 rely/not-rely`.

---

## Outside-human checklist (Akzeptanz 4–5) — Owner forwards; Chair does not send

Copy/paste for the named outside person (Owner sends G1/G2 outreach — **not** Chair):

- [ ] Open synthetic URL → watermark `SIMULATED_NOT_OBSERVED`
- [ ] Open OBSERVED-001 URL → watermark `OBSERVED`
- [ ] Digests match the two hashes above (or evidence match confirms)
- [ ] All five Limitations visible; Access token none / no grant
- [ ] Reply rely / not-rely + one missing-thing sentence to `memoria-recovery@agentmail.to`

Done when Owner has **at least one** rely/not-rely reply for OBSERVED-001.

---

## Nicht Teil dieser Schritte

- Keine Secrets, keine PRS-/Kundeninhalte in der Antwort.
- Operator-Compose (neue Quittung erzeugen) ist **nicht** Aufgabe der Außenperson.
- Kein Konto anlegen, kein Token als Zugang behandeln.
- Chair / agents do **not** email outside humans.

## Staging / local fallback

Prod is live. If prod is down, Owner may give a staging base or run local:

```
cd second-eye && python -m http.server 8765
# http://127.0.0.1:8765/
# http://127.0.0.1:8765/?source=observed&id=OBSERVED-001
```