🌐 [English](README.md) · [Deutsch](README.de.md) · **Magyar**

> Ez a fordítás tájékoztató jellegű. Eltérés esetén az angol változat
> ([`README.md`](README.md)) az irányadó.

# GENESIS — a kút

Egy kérdés-elsőbbségű prototípus: valódi elsődleges forrású visszakeresés egy
kicsi, lefagyasztott, tartalom-címzett, közkincs filozófiai/vallási szövegekből
álló korpuszon. Nincs generált próza — források vagy egy becsületes, típusos
elutasítás. Nincsenek fiókok, nincs követés, nincs tárolt vagy továbbított
látogatói adat; kérdések soha nincsenek sehova elküldve, és soha nem hagyják
el a böngészőt.

Állapot: **prototípus / Engine v0**. Ez nem egy kész termék; a keretezés, a
pozicionálás és a további építés folyamatban van.

## Futtatás

```bash
python3 -m http.server 8017
# nyisd meg: http://localhost:8017/
```

Bármely statikus fájlszerver működik — tiszta HTML/CSS/JS, nincs build lépés,
nincs függőség a Python 3-on és egy böngészőn kívül. A `well.js` ugyanabból a
könyvtárból tölti be a `corpus.json`-t, tehát HTTP-n keresztül szolgáld ki
(egy `file://` URL blokkolja a fetchet; az oldal így is renderelődik, és a
motor kiadja becsületes `ENGINE_UNREACHABLE` elutasítását).

## Mi van itt

| Útvonal | Szerep |
|---|---|
| `index.html`, `styles.css`, `well.js` | Az oldal: egy üres terminál → három ablak egy eredményen (**I** források, **II** motor, **III** a projekt valódi történetének élő pillantása) |
| `corpus.json` | korpus 0.4 — lefagyasztva, tartalom-címzett: 358 szakasz, 5 közkincs forrás (korpus 0.3, 293 szakasz / 4 forrás, szó szerint megőrizve `corpus-0.3.json` néven) |
| `corpus-src/*.txt` | A normalizált forrásszövegek (Tao Te Ching/Legge; Isha+Katha+Mundaka+Kena+Prasna Upanisadok/Müller; Bhagavad Gita/Arnold; KJV-válogatás; a teljes Jób könyve/KJV), eredetmegjelöléssel minden fejlécben |
| `build_corpus.py` | Újra lefagyasztja a `corpus-src/`-t `corpus.json`-ná (verziószám emelése új tartalomnál — egy korpuszt soha nem módosítanak a helyén) |
| `probes/` | Egy lefagyasztott, kurált próbahalmaz + egy fagyasztás-idejű szkript, amely visszakeresést futtat a valódi motor ellen, és egy receiptet ír (találat/hiba próbánként, a korpusz manifest-hasheéhez kötve) |
| `spine/` | Egy kis halmaz kurált kérdés, valódi, sémával validált eseményekhez (`genesis.event.v1`) kötve, amelyek a III. ablak pillantásában jelennek meg — soha nem valódi látogatói kérdések, soha senki tényleges bemenete |
| `capture.py` | Az ellenőrző keretrendszer: automatizált vizsgálatok normál / no-JS / csökkentett mozgás mellett, egy valódi böngészőt vezérel CDP-n keresztül |
| `variant-a/b/c.html` | Három korábbi vizuális irány-összehasonlítás (megőrizve az emlékezet kedvéért) |
| `tools/validate_genesis_events.py`, `maker-handshake/schemas/` | Szó szerint átvéve a `PhoenixAddictionary/memoria-mcp@81a79ce`-ból (2026-09-16) — a `spine/spine.jsonl`-t validálja a `genesis.event.v1` séma ellen. Nincs módosítva; séma-változásnál újra át kell venni a forrásból. |
| `PLUG-IN.md`, `.well-known/agent.json`, `AGENTS.md` | A hozzájárulási ajtó külső emberi vagy ágens hozzájárulóknak: mi nyitott, hogyan vedd el, hogyan add vissza. Kezdd a `PLUG-IN.md`-vel. |
| `packets/`, `receipts/`, `tools/validate_packet.py` | A csomag-/receipt-szerződés eme ajtó mögött (`genesis.packet.v1`, `genesis.receipt.v1`) — egy határolt, hash-indexelt nyitott munkaegység és a hozzá tartozó, géppel ellenőrzött munkabizonyíték. |
| `spine/live.jsonl`, `tools/generate_live_tick.py`, `.github/workflows/live-tick.yml` | A III. ablak „live now" sora: egy `genesis.live-tick.v1` rekord minden `main`-re történő push után (build-idejű ütem — soha a látogató böngészőjének órája), amely csak `gast` (vendég — egy push, amely vendég-receiptet adott hozzá) és differenciálatlan `projekt` között különböztet — lásd `spine/schemas/genesis.live-tick.v1.schema.json` az okért. |
| `LICENSE`, `LICENSING.md` | Három licenc háromféle tartalomhoz (kód, korpusz, generált kimenet) — lásd `LICENSING.md`, hogy melyik hol érvényes. |
| `de/`, `hu/`, `robots.txt`, `sitemap.xml` | Az `index.html` lokalizált másolatai (német, magyar) plusz a hreflang-váz (`<link rel="alternate" hreflang="…">` minden verzión, önmagára hivatkozó `<link rel="canonical">`, egy sitemap ugyanezekkel az annotációkkal). Maga a visszakereső motor csak angolul működik — az angol `corpus.json`-t keresi, függetlenül az oldal nyelvétől, ez a lokalizált oldalakon közvetlenül a beviteli mező mellett fel van tüntetve. A `PLUG-IN.de.md`/`PLUG-IN.hu.md`, `README.de.md`/`README.hu.md`, `AGENTS.de.md`/`AGENTS.hu.md` fedi le a dokumentumokat; mindegyik az angol eredetit nevezi meg irányadónak eltérés esetén. |

## Hozzájárulás

Külső hozzájárulások, emberi vagy ágens részről, egy ajtón mennek keresztül:
lásd [`PLUG-IN.md`](PLUG-IN.md). Géppel olvasható forma: `.well-known/agent.json`.

## Alapelvek

- **Források vagy csend.** Egy válasz vagy egy visszakereshető szakaszban
  gyökerezik (kivonattal, hellyel és hashsel megmutatva), vagy a motor
  becsületesen megmondja — soha nem egy komponált, forrás nélküli válasz.
- **Nincs gyűjtött, tárolt vagy továbbított látogatói adat.** A kérdéseket
  teljes egészében a böngészőben dolgozzák fel a helyi korpusz-fájl ellenében.
- **Semmi a képernyőn valódi mechanizmus nélkül mögötte.** Nincs kitalált
  aktivitás, nincs kitalált szám, nincs díszített üresség.

## Ellenőrzés

```bash
python3 capture.py   # a szervert a :8017-en várja; helyi Chrome kell hozzá
```

A CI (`.github/workflows/ci.yml`) minden push/PR-nél lefut: az átvett
`genesis.event.v1` validátor (+ saját tesztsorozata) a `spine/spine.jsonl`
ellen, a `genesis.live-tick.v1` validátor (+ saját tesztsorozata) a
`spine/live.jsonl` ellen, a `genesis.packet.v1`/`genesis.receipt.v1`
validátor (+ saját tesztsorozata) a `packets/`, `receipts/` és
`packets/INDEX.json` ellen, és a valódi `capture.py` böngésző-sorozat
headless Chrome-on keresztül. A `.github/workflows/live-tick.yml` külön fut,
csak a `main`-re történő push-nál, és hozzáfűzi a tényleges live-tick sort
(lásd a fenti táblázatot).

**Szándékosan nincs bekötve:** a `verify_genesis_surface.py` és a zeuge
witness-/claim-detect próba (`witness_receipt.py`), mindkettő a
`memoria-mcp`-ből. Közvetlenül ellenőrizve (2026-09-17), nem feltételezve:
mindkét eszköz egy Verbum-checkoutra és a `maker-handshake/packets/<order>/`
work-order-struktúrára épül, amivel ez a statikus oldal-repó nem
rendelkezik, és a `witness_receipt.py` ráadásul a külső `zeuge` binárist
igényli, amely itt nincs csomagolva vagy telepítve. Ezek bekötése úgyis
egy olyan ellenőrzést hozna létre, amely mindig hiányt jelent, vagy nem
alkalmazható — egy hamis zöld (vagy piros), nem egy valódi. Akkor válnak
relevánssá, amikor ez a repó egy élő, Verbum-alapú motorral integrálódik
(H3), vagy saját work-order-/csomag-folyamatot kap.
