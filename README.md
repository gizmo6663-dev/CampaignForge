# 🎲 Campaign Forge

**Campaign Forge** er en D&D 5e Game Master-app for Android, bygget på Kivy. En dedikert companion-app for Game Masters med karakterarkstøtte, terning-rollere, musikk, ambient-lyder, og Chromecast-streaming.

## ✨ Funksjoner

### 📁 Bilder
- Mappenavigasjon med bildebrowser
- Lokal lagring: `/sdcard/Documents/CampaignForge/images/`
- Støtt for PNG, JPG, JPEG, WebP

### 🎵 Musikk
- Lokal musikk-spiller (Android MediaPlayer via jnius)
- Play/Stop-kontroller
- Lagring: `/sdcard/Documents/CampaignForge/music/`
- Format: MP3, WAV, OGG

### 🌫️ Ambient
- Ferdiglaget atmosfærer fra Internet Archive
- Valg: Tavern, Forest, Castle, Battle
- Streamet over WiFi

### 🎲 Verktøy
- **D20-roller** med bonus
- **Generisk terning-roller** (f.eks `2d6+3`)
- **Initiative tracker** med automatisk rollinger
- Resultat-visning i real-time

### 👥 Karakterer
- **D&D 5e karakterark** med full detaljer
- Ability Scores (STR, DEX, CON, INT, WIS, CHA)
- HP, AC, Level, Alignment
- Skills og proficiencies
- JSON-lagring: `characters.json`
- **Karakterdetalj-visning** med alle stats

### 📺 Chromecast
- Device discovery
- Sender bilder/musikk til TV
- Krever `pychromecast`

---

## 🛠️ Setup

### Systemkrav
- **Android 5.0+** (minapi 21)
- **Python 3.9+**
- **Buildozer** + **Cython < 3.0**

### Bygge APK (lokalt)

```bash
pip install buildozer "cython<3.0"
buildozer android debug
