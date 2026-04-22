# Eldritch Portal

**A Keeper's Companion — a Kivy-based Android app for Call of Cthulhu and Pulp Cthulhu**

Eldritch Portal is a tabletop RPG companion built specifically for Lovecraftian roleplaying. The app bundles everything a Keeper needs during a session: an image library, mood sounds, weapon lookup, scenario tracker, and initiative tracker — all inside a dark, brooding interface that suits the genre. The phone can cast images and maps to a TV via Chromecast so your players see exactly what you want them to see.

Theme: **Abyssal Purple** — deep purple-black, burgundy, and muted gold.
Version: **0.3.3** · Language: Norwegian (UI) · System: Call of Cthulhu / Pulp Cthulhu

> The app's user interface is in Norwegian. This README uses English throughout but preserves the Norwegian tab names in parentheses so you can match them with what you see on screen.

---

## Contents

- [Features](#features)
- [Screenshots](#screenshots)
- [Getting started](#getting-started)
- [Scenario format](#scenario-format)
- [On-device folder layout](#on-device-folder-layout)
- [Building](#building)
- [Technical architecture](#technical-architecture)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Roadmap](#roadmap)

---

## Features

The app is split across six main tabs. Several of them carry sub-tabs to keep complex features organised:

### 🖼️ Images (Bilder)
- Gallery with folder navigation to organise images per scenario or campaign
- Large preview frame in gold — fade-in animation between image swaps
- Tap an image to display it; optional auto-cast to TV at the same time
- Recognises `.png`, `.jpg`, `.jpeg`, `.webp`

### 🔊 Sound (Lyd)
Combined tab with two sub-tabs, **Music** and **Ambient**:

**Music (Musikk)** — local playback
- Reads `.mp3`, `.ogg`, `.wav`, `.flac` from the `music/` folder
- Persistent mini-player at the bottom (Play/Pause/Next/Previous) that stays visible when you switch tabs
- Uses Android MediaPlayer via `pyjnius` for stable background playback

**Ambient** — mood sounds streamed from Internet Archive
- Categories include nature, storms, night forests, and importantly horror/dread — ideal for Cthulhu atmosphere
- Separate volume control from the music channel, so you can mix a rainy night with an eerie drone underneath
- No uploads required — links point to curated public-domain tracks

### ⚔️ Combat (Kamp)
Sub-tabs for combat support:

**Initiative (Initiativ)** — CoC/Pulp Cthulhu tracker
- Add investigators and enemies from the character list, or enter them ad hoc
- DEX-based initiative ordering (CoC standard)
- Round counter with active-participant indicator
- HP updates straight from the tracker

**Map (Kart)** — battlemap for combat scenes
- Activates automatically once you have combat participants
- 16:9 canvas optimised for TV casting
- Token composition through Pillow (PIL)

### 🧰 Tools (Verktøy)
Sub-tabs for session prep and quick reference:

**Characters (Karakterer)** — investigator roster
- CoC/Pulp Cthulhu character sheets with skills, background, and notes
- PCs and NPCs are visually distinguished by colour
- Stored in `characters.json` on device

**Weapons (Våpen)** — CoC weapon database
- A bundled `weapons.json` ships inside the APK (no external file needed)
- Search, filter by category, flag favourites
- Covers classic CoC eras: 1920s pulp, modern, and so on
- Overridable: drop your own `weapons.json` in the Documents folder to extend it

**Scenario** — tracker for pre-written scenarios
- Loads a `scenario.json` with structured data from the scenario you are running
- Four views (sub-sub-tabs): **Clues (Ledetråder)** · **Timeline (Tidslinje)** · **Plot (Plot)** · **Notes (Notater)**
- Tick off clues as the investigators find them; watch the timeline unfold
- Notes are editable live during the session
- The scenario file lives in app-private storage (avoiding Android 13+ scoped storage problems), with **Choose file** and **Import** buttons to pull it in from Documents

### 📖 Rules (Regler)
- Collapsible folder layout with CoC/Pulp Cthulhu references
- Overlay view for rule content — no network required
- Quick lookup mid-session

### 📺 Cast
- Discovers Chromecast devices on the local network via mDNS
- Casts images and battlemaps directly to a TV
- Local HTTP server (port 8089) serves media to the Chromecast
- Auto-cast: images cast automatically when shown if a device is connected

---

## Screenshots

*Screenshots to be added.*

---

## Getting started

### Installing on a device

1. Download the latest `EldritchPortal.apk` from [Releases](https://github.com/gizmo6663-dev/EldritchPortal/releases) or from GitHub Actions artefacts
2. Enable installation from unknown sources in Android settings
3. Install the APK and launch the app
4. Grant storage and network permissions when prompted
5. Restart the app so the folders are actually created

### First launch

On first launch the app creates this folder layout automatically:

```
Documents/EldritchPortal/
├── images/          ← image library (subfolders supported)
├── music/           ← local music tracks
├── characters.json  ← created when you make your first character
└── scenario.json    ← optional, imported from the Scenario tab
```

The weapon data (`weapons.json`) is bundled with the app, so nothing extra is needed to use the Weapons tab.

---

## Scenario format

The Scenario tab reads a `scenario.json` with the following structure:

```json
{
  "title": "Slow Boat to China",
  "system": "Pulp Cthulhu",
  "clues": [
    {"text": "The captain's diary mentions a mysterious passenger",
     "where": "Cabin 3", "found": false}
  ],
  "timeline": [
    {"text": "22:00 — the passenger disappears",
     "where": "Deck 2", "found": false}
  ],
  "beats": [
    {"text": "Investigators discover the artefact",
     "where": "Act 2", "found": false}
  ],
  "notes": [
    {"text": "NPC X is actually in disguise...",
     "where": "Keeper", "found": false}
  ]
}
```

Fields:
- `title` — the scenario name (shown in the action bar)
- `system` — the game system (e.g. "Call of Cthulhu", "Pulp Cthulhu")
- `clues`, `timeline`, `beats`, `notes` — lists with one entry per item
  - `text` — the content to display
  - `where` — context (location, act, chapter)
  - `found` — boolean toggled during the session

Place `scenario.json` in `Documents/EldritchPortal/`, open the Scenario tab, and tap **Reload** or **Choose file**.

---

## On-device folder layout

All user data lives in `/sdcard/Documents/EldritchPortal/`:

| Path | Contents |
|---|---|
| `images/` | Image gallery (subfolders supported) |
| `music/` | Local music tracks |
| `characters.json` | Characters and NPCs |
| `scenario.json` | Scenario data (imported into app-private storage) |
| `weapons.json` | *Optional* — overrides the bundled weapon data |
| `crash.log` | Error log for debugging |

In addition the app stores live scenario state in app-private storage (`user_data_dir`) to avoid scoped-storage restrictions on Android 13+.

---

## Building

Eldritch Portal is built as an Android APK via GitHub Actions. The workflow at `.github/workflows/build-apk.yml` runs Buildozer inside a Docker container (`kivy/buildozer`).

### Build via GitHub Actions

1. Push changes to the `main` branch — a build starts automatically
2. Or dispatch the workflow manually via **Actions → Build APK → Run workflow**
3. Use the `clean_build: true` input to force a full rebuild (clears cache)
4. Download the APK from the job artefacts when the workflow finishes

### Local build

```bash
pip install buildozer==1.5.0 cython==0.29.36
buildozer -v android debug
# APK lands in bin/
```

---

## Technical architecture

### Core classes

- **`EldritchApp`** — main class, builds the UI, manages tabs and state
- **`MediaServer`** — local HTTP server that serves media to Chromecast
- **`CastMgr`** — wrapper around `pychromecast` for device discovery and control
- **`APlayer`** — Android MediaPlayer wrapper (via `pyjnius`) for music
- **`SPlayer`** — streaming player for ambient sounds
- **`FPlayer`** — fallback player for desktop/testing
- **`FilePicker`** — file picker used by scenario import
- **`RBox`**, **`RBtn`**, **`RToggle`**, **`FramedBox`** — custom widgets with background and corner radius

### Design rules

- **All custom background drawing happens in `canvas.before`** — never in `canvas` or `canvas.after`. Earlier versions suffered from a `RenderContext` stack-overflow crash that was fixed by centralising all canvas drawing here.
- **`markup=True`** is required on every label that uses `[color]` or similar tags.
- **The mini-player is persistent** — it lives outside the tab content area, so music doesn't "disappear" when you change tab.
- **Sub-tab state is remembered** via `hasattr` checks — you return to the same sub-tab you left.
- **Scoped-storage friendly**: weapon data is bundled with the APK, scenario state lives in `user_data_dir`, so the app works on Android 13+ without broad storage permissions.

### Dependencies

| Package | Role |
|---|---|
| `kivy` 2.3.0 | UI framework |
| `pyjnius` | Android MediaPlayer binding |
| `pychromecast` | Chromecast discovery and control |
| `zeroconf`, `ifaddr` | mDNS for Chromecast |
| `protobuf` | Chromecast protocol |
| `pillow` | Battlemap composition |
| `android` | Android platform API |

---

## Configuration

Key lines in `buildozer.spec`:

```ini
requirements = python3,kivy==2.3.0,pillow,android,pyjnius,pychromecast,zeroconf,ifaddr,protobuf,cython<3.0

android.api = 34
android.minapi = 21
android.ndk = 25b
android.enable_androidx = True

# Include weapons.json in the APK
source.include_patterns = weapons.json

p4a.branch = v2024.01.21
```

**Pinning notes:**
- `buildozer==1.5.0` — newer versions pass incompatible arguments to stable p4a
- `cython==0.29.36` — Cython 3.x breaks older Kivy versions
- `p4a.branch = v2024.01.21` — the tag format with `v` prefix and leading zeros is mandatory
- `android.enable_androidx = True` — without this Gradle tries to pull from jcenter.bintray.com and hits 403

---

## Troubleshooting

### The app crashes on launch
Check `/sdcard/Documents/EldritchPortal/crash.log`. The most common causes are missing permissions or a corrupt JSON file.

### Music will not play
- Confirm the files are in `music/` with a supported format (`.mp3`, `.ogg`, `.wav`, `.flac`)
- On some devices the app must be restarted after storage permission is granted

### Scenario will not load
- Check that `scenario.json` is in `Documents/EldritchPortal/` with valid JSON syntax
- Android 13+ may block reading from Documents; use the **Choose file** button to open a file picker
- The scenario is then copied to app-private storage and loaded from there on subsequent launches

### Weapons tab is empty
- The tab uses the bundled `weapons.json` inside the APK
- If it is empty, check that `source.include_patterns = weapons.json` is set in `buildozer.spec`
- You may also place your own `weapons.json` in `Documents/EldritchPortal/` to override

### Chromecast does not find the TV
- The phone and Chromecast must be on the same Wi-Fi network
- The HTTP server uses port 8089 — make sure it is not blocked
- The status line at the bottom shows local IP and cast availability

### Build error: "jcenter.bintray.com 403"
Add `android.enable_androidx = True` to `buildozer.spec` and run a `clean_build`.

---

## Roadmap

Potential future features:

- [ ] Dice roller (D100, bonus/penalty die)
- [ ] Sanity/Luck tracker integrated with the Characters tab
- [ ] Countdown timer for round time limits
- [ ] One-shot sound effects: door opening, scream, gunshot
- [ ] Handout gallery with dramatic reveal
- [ ] Scenario-notes export after a session

---

## Tested on

- Samsung Galaxy S25 Ultra · Android 15

## Development

Eldritch Portal is a hobby project developed alongside an active Pulp Cthulhu campaign. Contributions and suggestions are welcome via GitHub issues.

**Repository:** [gizmo6663-dev/EldritchPortal](https://github.com/gizmo6663-dev/EldritchPortal)

**Related project:** [Campaign Forge](https://github.com/gizmo6663-dev/CampaignForge) — a D&D 5e variant built on the same architecture, styled with the Emerald Grove theme.
