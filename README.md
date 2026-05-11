# Campaign Forge

**Dungeon Master's Companion — en Kivy-basert Android-app for D&D 5e**

Campaign Forge er en tabletop-RPG-companion bygd for Dungeons & Dragons 5e (2024-reglene). Appen samler alt en DM trenger under spilløkta: bildebibliotek, stemningslyder, one-shot-lydeffekter, fullstendig scenario-bygger, karakterark, initiativ-tracker og battlemap med Chromecast-støtte.

Tema: **Emerald Grove** — mosegrønt, pergament og varmt gull.
Versjon: **0.1.0** · Språk: Norsk · System: D&D 5e (2024)

---

## Innhold

- [Funksjoner](#funksjoner)
- [Skjermbilder](#skjermbilder)
- [Kom i gang](#kom-i-gang)
- [Mappestruktur på enheten](#mappestruktur-på-enheten)
- [Bygging](#bygging)
- [Teknisk arkitektur](#teknisk-arkitektur)
- [Konfigurasjon](#konfigurasjon)
- [Feilsøking](#feilsøking)
- [Veikart](#veikart)

---

## Funksjoner

Appen er delt i fire hovedfaner. Karakter- og Verktøy-fanene har sub-faner for å holde komplekse funksjoner organisert. Lyd-fanen har nå fire sub-faner:

### 🖼️ Bilder
- Galleri med mappenavigering for å organisere bilder per kampanje eller sesjon
- Stor preview-ramme i gull — fade-inn-animasjon mellom bildebytter
- Tapp et bilde for å vise det; valgfritt auto-cast til TV samtidig
- Gjenkjenner `.png`, `.jpg`, `.jpeg`, `.webp`

### 🔊 Lyd
Kombinert fane med sub-fanene **Musikk**, **Ambient**, **One-shot** og **Scenarier**:

**Musikk** — lokal avspilling
- Leser `.mp3`, `.ogg`, `.wav`, `.flac` fra `music/`-mappen
- Persistent mini-player nederst (Play/Pause/Neste/Forrige) som ikke forsvinner når du bytter fane
- Bruker Android MediaPlayer via `pyjnius` for stabil bakgrunnsavspilling

**Ambient** — stemningslyder strømmet fra Internet Archive
- Tre kategorier tilpasset D&D-sjangeren: Natur · Steder · Stemning
- 13 kuraterte spor dekker alt fra en fredelig taverna til en tordenstorm over slagmarken
- Separat volumkontroll fra musikken, så du kan mikse kro-snakk under en oppdragsintroduksjon
- Ingen opplasting nødvendig — lenkene peker rett på public-domain-spor

**One-shot** — lydeffekter
- Leser lydeffekter fra `oneshots/`-mappen (`.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.aac`)
- Tapp en fil for å fyre den av — overlappende avspilling støttes
- Separat volumkontroll; "Stopp alle"-knapp for å avbryte klinger
- Typisk bruk: sverdklang, tordenbrak, dørsmell, trollformel

**Scenarier** — scenario-bygger og live-spiller
- Bygg scenarioer med Vogler-dramaturgiens 12 stadier som utgangspunkt
- Hvert scenario inneholder scener; hver scene har **loop-lag** (parallelle lydkilder) og **one-shot-knapper**
- Hvert loop-lag kan peke på musikk, ambient eller en lokal fil — alt loopes automatisk
- **Performance-modus**: skjuler redigeringsknapper og gjør play/stopp-knappene større for rask bruk under spill
- **Master-volum** per scenario justerer alle aktive lag i sanntid
- **Scene-overgang med fade-out**: lyder fades ut over 2 sekunder i stedet for å kuttes brått
- **Lag-bibliotek**: lagre og gjenbruk ferdigkonfigurerte lag på tvers av scenarioer
- Scene-rekkefølge kan endres med pil-knapper; scener kan dupliseres
- Lagres i privat app-lagring (`scenarios.json` og `library.json`)

### 🎭 Karakter
Sub-faner for karakterarbeid og kamp-støtte:

**Karakterer** — D&D 5e 2024-karakterark
- Full CRUD: opprett, rediger og slett karakterer
- Alle seks evner med automatisk modifier-beregning
- Ferdigheter med proficiency-toggles
- HP, AC, initiativ-bonus, conditions, spell slots og trollformler
- PC og NPC skilles visuelt med ulik fargekoding
- Lagres i privat app-lagring (`characters.json`)

**Initiativ** — kamp-tracker
- Legg til PCer/NPCer fra karakter-lista, eller ad hoc-fiender
- Skriv inn initiativ-kast, eller bruk «Auto-rull» (d20 + DEX-mod), sorter automatisk
- Bla gjennom runder og turer med aktiv-deltaker-indikator
- HP vises per deltaker; HP-justering (+1 / -1 / -5) er tilgjengelig i Battlemap-fanen sitt stat-panel for den som har turen

### 🧰 Verktøy
Samlet verktøyfane med sub-fanene **Battlemap**, **Regler** og **Cast**:

**Battlemap** — battlemap-komposisjon
- Komponér battlemap fra bakgrunnsbilde + token-overlegg
- 16:9 canvas (1280×720) optimalisert for TV-casting
- 5 ft per rute (D&D 5e-standard)
- Fog of war kan dekke hele kartet og avdekkes rute for rute
- Bruker Pillow (PIL) for bildebehandling — deaktiveres gracefully hvis PIL ikke er tilgjengelig
- Lagrer konfigurasjon i privat app-lagring og genererer `battlemap_current.png`

**Regler**
- Sammenleggbar mappestruktur med D&D 5e-referanser
- Overlay-visning for regel-innhold — ingen nettilgang nødvendig
- Raskt oppslag midt i spilløkta

**Cast**
- Oppdager Chromecast-enheter på lokalnett via mDNS
- Caster bilder og battlemaps direkte til TV
- Castet battlemap oppdateres fortløpende når kartet endres
- Lokal HTTP-server (port 8089) serverer media til Chromecast
- Auto-cast: bilder caster automatisk når de vises hvis en enhet er tilkoblet

---

## Skjermbilder

<table>
  <tr>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181637_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181637_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181644_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181644_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181649_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181649_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181656_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181656_CampaignForge.jpg" /></details></td>
  </tr>
  <tr>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181659_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181659_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181706_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181706_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181716_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181716_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181721_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181721_CampaignForge.jpg" /></details></td>
  </tr>
  <tr>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181732_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181732_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181742_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181742_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181749_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181749_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181753_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181753_CampaignForge.jpg" /></details></td>
  </tr>
  <tr>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181811_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181811_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181910_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181910_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181919_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181919_CampaignForge.jpg" /></details></td>
    <td align="center"><details><summary><img src="Screenshots/Screenshot_20260509_181931_CampaignForge.jpg" width="200" /></summary><img src="Screenshots/Screenshot_20260509_181931_CampaignForge.jpg" /></details></td>
  </tr>
</table>

---

## Kom i gang

### Installasjon på enhet

1. Last ned siste `CampaignForge.apk` fra [Releases](https://github.com/gizmo6663-dev/CampaignForge/releases) eller fra GitHub Actions-artefakter
2. Tillat installering fra ukjente kilder i Android-innstillinger
3. Installer APK-en og start appen
4. Gi tillatelser til lagring og nettverk når du blir spurt
5. Restart appen så mappene faktisk opprettes

### Første oppstart

Ved første oppstart oppretter appen denne mappestrukturen automatisk:

```
Dokumenter/CampaignForge/
├── images/          ← bildebibliotek (undermapper støttes)
├── music/           ← lokale musikkspor
├── oneshots/        ← korte lydeffekter for one-shot og scenarier
└── maps/            ← bakgrunnsbilder for battlemaps
```

JSON-data (karakterer, scenarioer, battlemap-konfig) lagres i appens **private lagring** og ikke i `/sdcard/Documents`. Disse filene migreres automatisk fra eldre installasjoner.

---

## Mappestruktur på enheten

**Brukerinnhold** (legg filer hit):

| Sti | Innhold |
|---|---|
| `/sdcard/Documents/CampaignForge/images/` | Bildegalleri (undermapper støttes) |
| `/sdcard/Documents/CampaignForge/music/` | Lokale musikkspor |
| `/sdcard/Documents/CampaignForge/oneshots/` | Lydeffekter for one-shot og scenario-lag |
| `/sdcard/Documents/CampaignForge/maps/` | Bakgrunnsbilder for battlemaps |

**App-data** (privat lagring — ikke synlig i filbehandler):

| Fil | Innhold |
|---|---|
| `characters.json` | Karakterer og NPCer |
| `scenarios.json` | Scenarioer med scener og lag |
| `library.json` | Gjenbrukbart lag-bibliotek |
| `battlemap.json` | Aktiv battlemap-konfigurasjon |
| `battlemap_current.png` | Generert kompositt for casting |
| `crash.log` | Feillogg for debugging |

---

## Bygging

Campaign Forge bygges som Android APK via GitHub Actions. Workflow-en i `.github/workflows/build-apk.yml` bruker Buildozer inne i en Docker-container (`kivy/buildozer`).

### Bygg via GitHub Actions

1. Push endringer til `main`-branchen — bygging starter automatisk
2. Eller kjør workflow manuelt via **Actions → Build APK → Run workflow**
3. Bruk `clean_build: true`-input hvis du vil tvinge full rebuild (tømmer cache)
4. Last ned APK fra job-artefakter når workflow er ferdig

### Lokal bygging

```bash
pip install buildozer==1.5.0 cython==0.29.36
buildozer -v android debug
# APK havner i bin/
```

---

## Teknisk arkitektur

### Kjerne-klasser

- **`CampaignForgeApp`** — hovedklasse, bygger UI, håndterer faner og state; arver `ScenariosMixin`
- **`ScenariosMixin`** (`scenarios.py`) — alt scenario-relatert UI og logikk; mixin på `CampaignForgeApp`
- **`MediaServer`** — lokal HTTP-server for å serve media til Chromecast
- **`CastMgr`** — innpakning rundt `pychromecast` for enhetsoppdagelse og kontroll
- **`APlayer`** — Android MediaPlayer-wrapper (via `pyjnius`) for musikk
- **`SPlayer`** — streaming-spiller for ambient-lyder
- **`FPlayer`** — fallback-spiller for desktop/testing
- **`LayerPlayer`** (`audio_layers.py`) — looper én lydkilde (lokal fil eller URL) med eget volum; brukes av scenario-lag
- **`OneShotPlayer`** (`audio_layers.py`) — fyrer av korte SFX med automatisk opprydding; støtter overlappende avspilling og fade-out
- **`RBox`**, **`RBtn`**, **`RToggle`**, **`FramedBox`** — tilpassede widgets med bakgrunn og hjørneradius

### Designregler

- **All tilpasset bakgrunnstegning skjer i `canvas.before`** — aldri i `canvas` eller `canvas.after`. Dette forhindrer at innhold gjemmes bak bakgrunnen og unngår krasj i render-stacken.
- **`markup=True`** er påkrevd på alle labels som bruker `[color]` eller lignende tags.
- **Mini-player er persistent** — den lever utenfor fane-content-området slik at musikken ikke forsvinner når du bytter fane.
- **Sub-fane-state huskes** via `hasattr`-sjekker — du kommer tilbake til samme sub-fane du forlot.
- **JSON-data lagres i privat app-lagring** (`ANDROID_PRIVATE`) — unngår avhengighet av eksternt lagringstillatelse for skriving.

### Avhengigheter

| Pakke | Rolle |
|---|---|
| `kivy` | UI-rammeverk |
| `pyjnius` | Android MediaPlayer-binding |
| `pychromecast` | Chromecast-oppdagelse og kontroll |
| `zeroconf`, `ifaddr` | mDNS for Chromecast |
| `protobuf` | Chromecast-protokoll |
| `pillow` | Battlemap-komposisjon (valgfri — battlemap-funksjonen deaktiveres gracefully uten) |
| `android` | Android plattform-API |

---

## Konfigurasjon

Viktige linjer i `buildozer.spec`:

```ini
requirements = python3,kivy,pillow,android,pychromecast,zeroconf,ifaddr,protobuf

android.api = 35
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a
android.enable_androidx = True
android.private_storage = True

p4a.bootstrap = sdl2
```

**Pinning-notater:**
- `buildozer==1.5.0` — nyere versjoner har inkompatible argumenter med stabil p4a
- `cython==0.29.36` — Cython 3.x bryter med eldre Kivy-versjoner (brukes ved lokal bygging)
- `android.enable_androidx = True` — uten denne prøver Gradle å hente fra jcenter.bintray.com (403)
- `android.private_storage = True` — app-data skrives til privat lagring, ikke `/sdcard`

---

## Feilsøking

### Appen krasjer ved oppstart
Koble til `adb logcat` eller finn `crash.log` i appens private lagring. De vanligste årsakene er manglende tillatelser eller korrupt JSON-fil.

### Musikk spilles ikke
- Bekreft at filene ligger i `music/` og har støttet format (`.mp3`, `.ogg`, `.wav`, `.flac`)
- På noen enheter må appen restartes etter at lagringstillatelse er gitt

### Ambient-lyder laster ikke
- Ambient-lyder strømmes fra Internet Archive — krever nettilgang
- Hvis en spesifikk URL er død, oppdater `AMBIENT_SOUNDS`-lista i `cf_common.py`

### One-shot-lyder vises ikke
- Legg lydfilene i `oneshots/`-mappen under `Documents/CampaignForge/`
- Støttede formater: `.mp3`, `.ogg`, `.wav`, `.flac`, `.m4a`, `.aac`

### Scenarier-lyd spilles ikke
- Loop-lag må konfigureres med kilde (Musikk, Ambient eller Egne) via Endre-knappen
- Lokale lyder for lag hentes fra `music/`- eller `oneshots/`-mappen
- Ambient-lag krever nettilgang

### Battlemap-fanen fungerer ikke
- Battlemap krever Pillow — sjekk at `pillow` står i `requirements` i `buildozer.spec`
- Bakgrunnsbilder må ligge i `maps/`-mappen

### Chromecast finner ikke TV
- Telefonen og Chromecast må være på samme Wi-Fi
- HTTP-serveren bruker port 8089 — sjekk at den ikke er blokkert
- Statuslinjen nederst viser lokal IP og cast-tilgjengelighet

### Build-feil: "jcenter.bintray.com 403"
Legg til `android.enable_androidx = True` i `buildozer.spec` og kjør `clean_build`.

### Build-feil: "unknown argument --dir"
Pin til `buildozer==1.5.0` i workflow-filen.

---

## Veikart

Mulige fremtidige funksjoner:

- [ ] Terningkast-verktøy (D&D-terningsett: d4, d6, d8, d10, d12, d20, d100)
- [ ] Nedtellingstimer for sesjonspauser eller rundetidsbegrensning
- [ ] Sesjonsnotater med timestamps
- [ ] Eksport/import av karakterer
- [ ] Custom ambient-URL-liste redigerbar i appen
- [ ] Flere regel-referanser i Regler-fanen

---

## Testet på

- Samsung Galaxy S25 Ultra · Android 15

## Utvikling

Campaign Forge er et hobbyprosjekt utviklet for aktive D&D 5e-kampanjer. Bidrag og forslag tas imot via issues på GitHub.

**Repository:** [gizmo6663-dev/CampaignForge](https://github.com/gizmo6663-dev/CampaignForge)

**Søster-prosjekter:**
- [EldritchPortal](https://github.com/gizmo6663-dev/EldritchPortal) — Call of Cthulhu / Pulp Cthulhu-variant med Abyssal Purple-tema (norsk)
- [EldritchPortals](https://github.com/gizmo6663-dev/EldritchPortals) — engelsk versjon av EldritchPortal
