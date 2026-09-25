# Second Eye — Außenperson / Outside person (Akzeptanz 4–5)

**Ziel / Goal:** Eine veröffentlichte Quittung prüfen und dem Owner **rely / not-rely** melden.  
Kein Konto, keine Zertifizierung, kein Zugang (`no grant`).

Chair A: `claimClass` ist `OBSERVED` **oder** `SIMULATED_NOT_OBSERVED`. Das Spielzeug (synthetic) bleibt simuliert.

---

## Fünf Schritte (frozen)

### 1. Synthetisches Spielzeug öffnen
URL: **`/second-eye/`**  
(ohne Query = synthetic)

**Prüfen:** Wasserzeichen / watermark oben = **`SIMULATED_NOT_OBSERVED`**.  
claimClass-Zeile gleich. Digest-Match darf „n/a for synthetic toy“ sagen.

### 2. Beobachtete Quittung öffnen
URL: **`/second-eye/?source=observed&id=OBSERVED-001`**

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

**Owner inbox (Kanal — Owner füllt aus):** `[OWNER_INBOX_CHANNEL]`  
Beispiel-Platzhalter: E-Mail / Signal / Thread — nur Owner setzt den echten Kanal.

---

## Nicht Teil dieser Schritte

- Keine Secrets, keine PRS-/Kundeninhalte in der Antwort.
- Operator-Compose (neue Quittung erzeugen) ist **nicht** Aufgabe der Außenperson.
- Kein Konto anlegen, kein Token als Zugang behandeln.

## Staging-Hinweis

Wenn die Seite noch nicht live ist: Owner gibt die Staging-Basis-URL; hängen Sie die Pfade aus Schritt 1–2 daran, z. B.  
`https://<staging-host>/second-eye/` und  
`https://<staging-host>/second-eye/?source=observed&id=OBSERVED-001`.
