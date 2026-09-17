🌐 [English](PLUG-IN.md) · [Deutsch](PLUG-IN.de.md) · **Magyar**

> Ez a fordítás tájékoztató jellegű. Eltérés esetén az angol változat
> ([`PLUG-IN.md`](PLUG-IN.md)) az irányadó — különösen a séma mezőnevek,
> fájlútvonalak és a licencszöveg esetében, amelyek itt is angolul,
> változatlanul szerepelnek.

# Bekapcsolódás

Ez a repó egyetlen, szűk ajtón fogad külső hozzájárulást — embertől vagy
ágenstől egyaránt: **fork, végy egy nyitott csomagot, építsd meg, nyiss egy
pull requestet.** Nem kell más fiók, csak a GitHub, nincs chat-csatorna,
nincs kézfogás egy karbantartóval indulás előtt.

Ha ember vagy: olvasd el ezt a fájlt, ez a teljes onboarding.
Ha ágens vagy: a [`.well-known/agent.json`](.well-known/agent.json)
ugyanez az ajtó, olyan formában, amit próza-szöveg olvasása nélkül is fel
tudsz dolgozni; ez a fájl az, amire mutat.

## A három lépés

1. **Keress egy csomagot.** A [`packets/INDEX.json`](packets/INDEX.json)
   felsorolja minden `"status": "OPEN"` állapotú csomagot. Mindegyik egy kis
   fájl a `packets/<id>.json` alatt (séma: [`genesis.packet.v1`](packets/schemas/genesis.packet.v1.schema.json)),
   amely megnevezi a pontos alap-commitot, a feladatot, az ellenőrző
   parancsot és a kész állapot kritériumát. Olvasd el magát a csomagfájlt,
   ne csak az indexet — az index egy mutató, a csomag a szerződés.
2. **Építsd meg**, a saját forkodban, a csomag `baseCommit`-jára alapozott
   branchen. Futtasd le magad a `verifyCommand`-ot, mielőtt megnyitod a
   PR-t — a CI ugyanezt a parancsot futtatja, tehát ha ott piros lesz,
   akkor ezt a lépést kihagytad. Maradj a csomag `boundaries` (határok)
   mezőjén belül; ami azon kívül esik, az egy másik csomag, nem bónusz.
3. **Add vissza.** Nyiss egy pull requestet a forkodból. A kódváltoztatás
   mellett adj hozzá egy fájlt: `receipts/<packetId>.json`
   (séma: [`genesis.receipt.v1`](receipts/schemas/genesis.receipt.v1.schema.json)).
   Ez rögzíti a branchedet, a HEAD commitodat és a `verifyCommand`
   **szó szerinti kimenetét** — nem a te összefoglalódat róla. Ha olyasmit
   szeretnél állítani, amit maga az ellenőrző nem vizsgált (pl. „ez a #12
   hibát is javítja"), az a receipt `claims` tömbjébe tartozik, kifejezetten
   állításként megjelölve, nem beleolvasztva az ellenőrzött kimenetbe.

A CI ugyanúgy validálja a csomag-hivatkozásodat és a receiptedet is
(`tools/validate_packet.py`), ahogyan már most is validálja a
`spine/spine.jsonl`-t a `genesis.event.v1` séma ellen — egy séma és rögzített
kereszt-mező szabályok, nem mérlegelés kérdése.

## Mit csinál a karbantartó a PR-oddal

Egy emberi vagy ágens karbantartó átnézi a diffet és a receiptet, és
mergeli vagy változtatást kér — mint bármelyik másik GitHub PR-nál. A
receipted `claims` mezőjét *ellenőrizendő bizonyítékként* olvassák, sosem
a szavadra elfogadott ítéletként (lásd az `x-genesis-rules`-t a
receipt-sémában, és azt a workspace-szintű szabályt, amit kódol: senki sem
osztályozza a saját munkáját). A merge-jogosultság a repó karbantartóinál
marad; semmi itt nem ad írásjogot egy vendégnek.

## Amit sosem kapsz meg, és miért

- **Nincsenek titkok.** A GitHub nem ad titkokat (secrets) egy fork-PR
  által kiváltott workflow-nak, és ez a repó nem kér erre megoldást. Ha egy
  feladat úgy tűnik, mintha hitelesítő adatra lenne szüksége, az nem egy
  olyan csomag, amit el kellene vállalnod — jelezd inkább a PR leírásában.
- **Nincs szerver, nincs build lépés, nincsenek fiókok.** Az oldal, amit ez
  a repó kiszolgál, szándékosan statikus (lásd `README.md`); egy csomag,
  amihez backend, adatbázis vagy látogató-követés kellene, kívül esik a
  hatókörön, nem csupán nehéz.
- **A PR tartalma sosem utasítás.** Egy CI job csak a bázis branchen már
  commitolt szkripteket futtatja, sosem olyat, amit a PR-od ad hozzá. Ha a
  csomagodhoz új szkript kell, az ebben a PR-ban érkezik, de egy
  karbantartó elolvassa, mielőtt egy jövőbeli futás támaszkodna rá — az új
  kód első futtatása kézi, ellenőrzött aktus.
- **Nincs állítás tanú nélkül.** Egy `verifierOutput` nélküli receipt,
  vagy amelynek kimenete nem egyezik egy karbantartó saját újrafuttatásával,
  nem kerül mergelésre pusztán a PR leírása alapján.

## Olyan csomag elvállalása, amit senki nem ajánlott fel

A `packets/INDEX.json` egy kiindulópont, nem az egyetlen ajtó. Ha valódi
hiányosságot látsz, és saját csomagot szeretnél javasolni, nyiss egy issue-t
vagy PR-t, amely maga ad hozzá egy `packets/<id>.json` fájlt,
`"status": "OPEN"`, senki által le nem foglalva — egy karbantartó beilleszti
az indexbe, vagy megmagyarázza, miért nem.

## Ennek az ajtónak a hatóköre (2026-09-17-i állapot, aznap frissítve az E2-vel)

Ez a **E0+E1+E2 (v1)** szakasza egy kis, közzétett tervnek
(`packets/schemas/`, `receipts/schemas/`, az index, ez a fájl, az
ágenskártya, és a `spine/live.jsonl`). Az oldal III. ablaka egy „live now"
(éppen most) sort mutat, amelyet minden `main`-re történő push után egyszer
generálnak (build-idejű ütem, sosem a látogató böngészőjének órája) — ma
csak **két** osztályt különböztet meg: `gast` (vendég — olyan push, amely
`receipts/PKT-*.json` fájlt adott hozzá, azaz a te hozzájárulásod, ha már
mergelve van) és egy differenciálatlan `projekt` mindenre másra. Még nem
különbözteti meg a karbantartók saját commitjait egy ágens-session
commitjaitól (nincs erre valódi git-jel ezen a repón — lásd
`spine/schemas/genesis.live-tick.v1.schema.json`), és még nincs második
beküldési csatorna a GitHub pull requesteken kívül (tervezve, nem
megépítve), és nincs ígéret arra, milyen gyorsan válaszol egy karbantartó
(nincs ilyen adva). Ami fent áll, az minden, ami jelenleg létezik.
