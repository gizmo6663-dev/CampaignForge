# Campaign Forge

**Dungeon Master-verktøy for Dungeons & Dragons 5E (2024) — fullt støttet på Android.**

![Platform](https://img.shields.io/badge/platform-Android-green)
![D&D](https://img.shields.io/badge/D%26D-5E_2024-red)
![Pris](https://img.shields.io/badge/pris-gratis-brightgreen)
![Lisens](https://img.shields.io/badge/lisens-MIT-blue)

Campaign Forge er en alt-i-ett-app for DM-er som ønsker å samle sesjonsverktøyene sine på én telefon. Appen er utviklet for bruk **under pågående sesjoner** — alt er optimalisert for raske oppslag ved bordet, ikke for forberedelse hjemme.

**Appen er helt gratis og blir det alltid.** Ingen reklame, ingen kjøp i appen, ingen datainnsamling.

## Om utvikleren og hvordan appen er laget

Jeg er ikke utvikler av yrke. Campaign Forge er bygget av en hobbyist som ønsket et praktisk verktøy til egne sesjoner, og det meste av koden er skrevet i samarbeid med KI (Claude). Dette er ikke skjult — jeg nevner det fordi jeg tenker at brukerne bør vite det:

- **Fordelene:** Utviklingen har gått raskt, noe som har latt meg legge til funksjoner etter behov fra pågående kampanjer. Koden er godt kommentert og strukturert.
- **Begrensningene:** Jeg kan ikke alltid garantere hvordan koden oppfører seg i alle edge cases, og jeg finner ikke nødvendigvis feil raskt selv. Rapporter gjerne via [Issues](https://github.com/gizmo6663-dev/CampaignForge/issues) — jeg setter pris på alle tilbakemeldinger.
- **Hvis du kan kode selv:** Pull requests og forslag er veldig velkomne. Hele kildekoden ligger åpent her.

## Funksjoner

- **Karakterhåndtering** — full støtte for D&D 5E 2024-karakterark (PC og NPC). Lagrer alle 18 ferdigheter, evneverdier, spell slots (nivå 1-9), attunement, mynter og beskrivelsesfelt. Modifier og skill-bonuser regnes ut automatisk.
- **Initiativ-tracker** — bygg initiativrekken fra lagrede karakterer eller velg blant 65 vanlige D&D-fiender (Goblin → Pit Fiend). Auto-rull d20+DEX for alle, sortér automatisk, trykk på aktiv karakter for å gå videre til neste.
- **Regelfane** — 17 kategorier med oppslag for DM under spill: grunnregler, kamprunde, conditions, magi, spell-referanse, monsterreferanse, encounter design, DC-referanse, loot-tabeller, kampanjeverktøy m.m.
- **Bildegalleri** — mappebasert galleri for scene-illustrasjoner, karakterbilder og kart. Cast til Chromecast for visning på TV.
- **Musikkspiller** — spill av egen lokalmusikk med mini-player som følger deg mellom faner.
- **Ambient-avspilling** — 20+ forhåndsvalgte streamingkilder for regn, storm, nattlyder, horror-atmosfærer osv. (leveres fra Internet Archive).
- **Chromecast-støtte** — send bilder og lyd til TV via lokal HTTP-server.

## Installasjon

**Ferdig APK:** Last ned siste bygg fra [Releases](https://github.com/gizmo6663-dev/CampaignForge/releases). Du må tillate installasjon fra ukjente kilder på Android.

**Bygg selv:**
```bash
git clone https://github.com/gizmo6663-dev/CampaignForge
cd CampaignForge
# Via GitHub Actions: trigger "Build APK"-workflow manuelt
```

**Krav:** Android 5.0+ (API 21 eller høyere). Testet på Samsung Galaxy S25 Ultra.

## Bruk

Første gang du åpner appen, oppretter den `/sdcard/Documents/CampaignForge/` med undermapper for bilder og musikk. Legg filer der for at de skal dukke opp i appen.

**Karakteroppretting:**
1. Åpne *Karakter*-fanen, trykk *+ Ny*
2. Fyll inn IDENTITET, sett Proficiency Bonus basert på nivå
3. Sett ability scores — modifier regnes automatisk
4. Huk av Save Prof-togglene for relevante evner
5. Under FERDIGHETER: huk av Prof (og evt. Exp for expertise). Bonus regnes og vises i sanntid.

**Initiativ under kamp:**
1. Bytt til *Initiativ*-undertab
2. Trykk *+ PC/NPC* for å legge til lagrede karakterer
3. Trykk *+ Fiende* og velg fra lista, eller skriv inn egendefinert navn
4. *Auto-rull alle* eller fyll inn manuelt, trykk *Fullfør*
5. Det øverste kortet er aktiv karakter — trykk på det når turen er ferdig

## Datalagring

Alle karakterer og egne filer ligger lokalt på telefonen. Ingenting sendes til nettet (utenom Chromecast, som kun sender til din egen TV).

Data-plassering:
- `/sdcard/Documents/CampaignForge/characters.json` — lagrede karakterer
- `/sdcard/Documents/CampaignForge/images/` — egne bilder
- `/sdcard/Documents/CampaignForge/music/` — egne musikkfiler

## Teknisk

Skrevet i Python med Kivy-rammeverket. Android-ytelse via pyjnius (bruker Android MediaPlayer direkte). Bygges med Buildozer via python-for-android.

**Hovedavhengigheter:** kivy, pillow, pychromecast, zeroconf, pyjnius

## Bidra

Forslag og feilrapporter tas gjerne imot via [Issues](https://github.com/gizmo6663-dev/CampaignForge/issues). Hvis du savner spesifikke monstre i initiativ-trackeren eller regler i regelfanen, skriv en issue.

## Lisens

MIT — se `LICENSE`-filen. Appen er utviklet privat og er ikke tilknyttet Wizards of the Coast. Dungeons & Dragons og tilhørende logoer er varemerker tilhørende Wizards of the Coast LLC. Regelhenvisningene i appen er omskrevet DM-referanser, ikke reproduksjon av regelteksten.

## Relaterte prosjekter

- **[Eldritch Portal](https://github.com/gizmo6663-dev/EldritchPortal)** — søsterapp for Call of Cthulhu og Pulp Cthulhu.
