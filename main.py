import os, sys, traceback, socket, threading, json, random
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from kivy.clock import Clock

LOG = "/sdcard/Documents/CampaignForge/crash.log"
os.makedirs(os.path.dirname(LOG), exist_ok=True)
def log(msg):
    with open(LOG, "a") as f:
        f.write(msg + "\n")
log("=== APP START (CampaignForge v0.1.0) ===")

try:
    from kivy.app import App
    from kivy.uix.boxlayout import BoxLayout
    from kivy.uix.floatlayout import FloatLayout
    from kivy.uix.gridlayout import GridLayout
    from kivy.uix.scrollview import ScrollView
    from kivy.uix.button import Button
    from kivy.uix.togglebutton import ToggleButton
    from kivy.uix.label import Label
    from kivy.uix.image import Image
    from kivy.uix.slider import Slider
    from kivy.uix.spinner import Spinner
    from kivy.uix.textinput import TextInput
    from kivy.uix.widget import Widget
    from kivy.core.window import Window
    from kivy.utils import platform
    from kivy.metrics import dp, sp
    from kivy.animation import Animation
    from kivy.properties import ListProperty, NumericProperty
    from kivy.lang import Builder
    log("Kivy imported OK")

    CAST_AVAILABLE = False
    try:
        import pychromecast
        CAST_AVAILABLE = True
    except ImportError:
        pass
    USE_JNIUS = False
    MediaPlayer = None
    if platform == 'android':
        try:
            from jnius import autoclass
            MediaPlayer = autoclass('android.media.MediaPlayer')
            USE_JNIUS = True
            log("Using Android MediaPlayer")
        except:
            pass

    BASE_DIR  = "/sdcard/Documents/CampaignForge"
    IMG_DIR   = os.path.join(BASE_DIR, "images")
    MUSIC_DIR = os.path.join(BASE_DIR, "music")
    CHAR_FILE = os.path.join(BASE_DIR, "characters.json")

    def ensure_dirs():
        """Opprett mapper ETTER tillatelser er gitt."""
        for d in [IMG_DIR, MUSIC_DIR]:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                log(f"makedirs {d}: {e}")
        log(f"Dirs OK: {os.path.exists(IMG_DIR)}, {os.path.exists(MUSIC_DIR)}")

    # === FARGER – TAVERN LIGHT (D&D tema, lysere) ===
    BG   = [0.13, 0.09, 0.07, 1]      # varm moerk brun (som laer i peisglans)
    BG2  = [0.20, 0.13, 0.10, 1]      # lysere panel (pergament-skygge)
    BTN  = [0.38, 0.20, 0.13, 1]      # knapp (varm laer-brun)
    BTNH = [0.60, 0.28, 0.18, 1]      # aktiv fane (kobber-roed)
    SHAD = [0.04, 0.02, 0.02, 0.5]    # skygge
    GOLD = [1.00, 0.82, 0.38, 1]      # lysere gull (D&D-aksent)
    GDIM = [0.68, 0.55, 0.28, 1]      # dempet gull
    TXT  = [0.96, 0.92, 0.80, 1]      # lys pergament-tekst
    DIM  = [0.72, 0.60, 0.48, 1]      # lysere laer-beige
    RED  = [0.85, 0.25, 0.18, 1]      # blod-roed (fare/stopp)
    GRN  = [0.40, 0.62, 0.32, 1]      # skogs-groenn (OK/PC)
    BLUE = [0.38, 0.52, 0.72, 1]      # staal-blaa (info)
    BLK  = [0.0, 0.0, 0.0, 1]         # svart (preview-bg)
    IMG_EXT   = ('.png','.jpg','.jpeg','.webp')
    HTTP_PORT = 8089

    # ============================================================
    # KV REGLER – skygge + avrundede hjørner
    # Skygge: en mørk RoundedRectangle forskjøvet 2dp ned.
    # Hoveddel: RoundedRectangle med bg_color oppå.
    # ============================================================
    Builder.load_string('''
<RBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    canvas.before:
        Color:
            rgba: self.shadow_color
        RoundedRectangle:
            pos: self.x, self.y - dp(2)
            size: self.width, self.height
            radius: [self.radius]
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]

<RToggle>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    canvas.before:
        Color:
            rgba: self.shadow_color
        RoundedRectangle:
            pos: self.x, self.y - dp(2)
            size: self.width, self.height
            radius: [self.radius]
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]

<RBox>:
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]

<FramedBox>:
    canvas.before:
        Color:
            rgba: self.frame_color
        Line:
            rectangle: (self.x, self.y, self.width, self.height)
            width: 1.5
''')

    class RBtn(Button):
        bg_color = ListProperty(BTN)
        shadow_color = ListProperty(SHAD)
        radius = NumericProperty(dp(14))

    class RToggle(ToggleButton):
        bg_color = ListProperty(BTN)
        shadow_color = ListProperty(SHAD)
        radius = NumericProperty(dp(14))

    class RBox(BoxLayout):
        bg_color = ListProperty(BG2)
        radius = NumericProperty(dp(20))

    class FramedBox(BoxLayout):
        frame_color = ListProperty(GOLD)

    # === LYDKILDER ===
    AMBIENT_SOUNDS = [
        {"name":"--- Natur ---"},
        {"name":"Regn og torden","url":"https://archive.org/download/RainSound13/Gentle%20Rain%20and%20Thunder.mp3"},
        {"name":"Havbølger","url":"https://archive.org/download/naturesounds-soundtheraphy/Birds%20With%20Ocean%20Waves%20on%20the%20Beach.mp3"},
        {"name":"Nattregn","url":"https://archive.org/download/RainSound13/Night%20Rain%20Sound.mp3"},
        {"name":"Vind og storm","url":"https://archive.org/download/rain-sounds-gentle-rain-thunderstorms/epic-storm-thunder-rainwindwaves-no-loops-106800.mp3"},
        {"name":"Nattlyder","url":"https://archive.org/download/rain-sounds-gentle-rain-thunderstorms/ambience-crickets-chirping-in-very-light-rain-followed-by-gentle-rolling-thunder-10577.mp3"},
        {"name":"Havstorm","url":"https://archive.org/download/naturesounds-soundtheraphy/Sound%20Therapy%20-%20Sea%20Storm.mp3"},
        {"name":"Lett regn","url":"https://archive.org/download/naturesounds-soundtheraphy/Light%20Gentle%20Rain.mp3"},
        {"name":"Tordenstorm","url":"https://archive.org/download/RainSound13/Rain%20Sound%20with%20Thunderstorm.mp3"},
        {"name":"Urolig hav","url":"https://archive.org/download/RelaxingRainAndLoudThunderFreeFieldRecordingOfNatureSoundsForSleepOrMeditation/Relaxing%20Rain%20and%20Loud%20Thunder%20%28Free%20Field%20Recording%20of%20Nature%20Sounds%20for%20Sleep%20or%20Meditation%20Mp3%29.mp3"},
        {"name":"--- Horror ---"},
        {"name":"Skummel atmosfære","url":"https://archive.org/download/creepy-music-sounds/Creepy%20music%20%26%20sounds.mp3"},
        {"name":"Uhyggelig drone","url":"https://archive.org/download/scary-sound-effects-8/Evil%20Demon%20Drone%20Movie%20Halloween%20Sounds.mp3"},
        {"name":"Mørk spenning","url":"https://archive.org/download/scary-sound-effects-8/Dramatic%20Suspense%20Sound%20Effects.mp3"},
        {"name":"Horrorlyder","url":"https://archive.org/download/creepy-music-sounds/Horror%20Sound%20Effects.mp3"},
    ]

    # === D&D 5E 2024 KARAKTERFELT ===
    DND_ABILITIES = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']

    # Hver ferdighet: (navn, evne)
    DND_SKILLS = [
        ('Acrobatics',      'DEX'),
        ('Animal Handling', 'WIS'),
        ('Arcana',          'INT'),
        ('Athletics',       'STR'),
        ('Deception',       'CHA'),
        ('History',         'INT'),
        ('Insight',         'WIS'),
        ('Intimidation',    'CHA'),
        ('Investigation',   'INT'),
        ('Medicine',        'WIS'),
        ('Nature',          'INT'),
        ('Perception',      'WIS'),
        ('Performance',     'CHA'),
        ('Persuasion',      'CHA'),
        ('Religion',        'INT'),
        ('Sleight of Hand', 'DEX'),
        ('Stealth',         'DEX'),
        ('Survival',        'WIS'),
    ]

    # === REGLER & REFERANSE ===
    # Komplett CoC 7e + Pulp Cthulhu keeper-referanse.
    RULES = [
      ("Grunnregler", "", [
        ("Ferdighetskast", [
          "Rull d100 (percentile) mot skill-verdi.",
          "Lik eller under = suksess.",
          "",
          "Suksessnivåer:",
          "  Critical: resultat = 01",
          "  Extreme: resultat \u2264 skill / 5",
          "  Hard: resultat \u2264 skill / 2",
          "  Regular: resultat \u2264 skill",
          "  Failure: resultat > skill",
          "",
          "Automatisk suksess: 01 alltid suksess.",
          "Fumble (basert på KRAV, ikke base skill):",
          "  Krav \u2265 50: kun 100 er fumble",
          "  Krav < 50: 96\u2013100 er fumble",
          "  Eks: skill 60, Hard diff (krav 30)",
          "    -> fumble på 96\u2013100",
        ]),
        ("Vanskelighetsgrad", [
          "Keeper setter vanskelighetsgrad:",
          "  Regular: skill-verdi (standard)",
          "  Hard: halv skill-verdi",
          "  Extreme: femtedel av skill-verdi",
          "",
          "Mot levende motstandere:",
          "  Motstanders skill < 50: Regular",
          "  Motstanders skill \u2265 50: Hard",
          "  Motstanders skill \u2265 90: Extreme",
        ]),
        ("Bonus & Penalty", [
          "Bonus die: rull 2 tier-terninger,",
          "  bruk den LAVESTE.",
          "Penalty die: rull 2 tier-terninger,",
          "  bruk den HØYESTE.",
          "",
          "Maks 2 bonus ELLER 2 penalty.",
          "Bonus og penalty kansellerer 1:1.",
          "",
          "Gis av Keeper basert på omstendigheter:",
          "  Fordel: bonus (godt lys, tid, verktøy)",
          "  Ulempe: penalty (stress, dårlig sikt)",
        ]),
        ("Pushed Rolls", [
          "Spiller kan pushe ETT mislykket kast.",
          "Må beskrive HVA de gjør annerledes.",
          "Keeper må godkjenne pushen.",
          "",
          "Mislykket push = ALVORLIG konsekvens",
          "(verre enn vanlig feil).",
          "",
          "KAN IKKE pushes:",
          "  SAN-sjekker",
          "  Luck-sjekker",
          "  Kamp-kast",
          "  Allerede pushede kast",
        ]),
        ("Opposed Rolls", [
          "Begge parter ruller sine skills.",
          "Høyeste suksessnivå vinner.",
          "Likt nivå: høyeste skill-verdi vinner.",
          "Ingen suksess: status quo.",
          "",
          "Vanlige opposed rolls:",
          "  Sneak vs Listen",
          "  Fast Talk vs Psychology",
          "  Charm vs POW",
          "  STR vs STR (bryte, holde)",
          "  DEX vs DEX (gripe, unnvike)",
          "  Disguise vs Spot Hidden",
        ]),
        ("Luck", [
          "Luck-verdi: 3d6 x 5 (ved opprettelse).",
          "Luck-sjekk: d100 \u2264 Luck.",
          "",
          "Spending Luck:",
          "  Etter et skill-kast: trekk Luck-poeng",
          "  1:1 for å senke resultatet.",
          "  Eks: kast 55, skill 50 -> spend 5 Luck.",
          "",
          "Luck regenereres IKKE i standard CoC.",
          "Pulp: regenerer 2d10 Luck per sesjon.",
          "",
          "Group Luck: laveste Luck i gruppen",
          "  brukes for tilfeldige hendelser.",
        ]),
        ("Erfaring & utvikling", [
          "Etter scenario: marker brukte skills.",
          "Rull d100 for hver markert skill:",
          "  Resultat > skill = +1d10 til skill.",
          "  Resultat \u2264 skill = ingen økning.",
          "",
          "Skill-maks: 99 (unntatt CM: 99).",
          "Alderseffekter kan senke stats.",
        ]),
      ]),
      ("Kamp", "", [
        ("Kampflyt", [
          "1. Alle handler i DEX-rekkefølge",
          "   (høyeste først).",
          "",
          "2. Hver deltaker får 1 handling:",
          "   - Angripe (melee eller ranged)",
          "   - Flee (trekke seg ut)",
          "   - Manøver (trip, disarm, etc.)",
          "   - Kaste besvergelse",
          "   - Bruke gjenstand / First Aid",
          "   - Annet (snakke, lete, etc.)",
          "",
          "3. Forsvarer velger reaksjon:",
          "   - Dodge (unngå)",
          "   - Fight Back (motangrep, kun melee)",
          "   - Ingenting (tar full skade)",
          "",
          "4. Gjenta til kamp er over.",
        ]),
        ("Melee", [
          "Angriper: rull Fighting-skill.",
          "Forsvarer velger:",
          "",
          "DODGE (opposed vs Dodge-skill):",
          "  Angriper vinner -> full skade",
          "  Forsvarer vinner -> unngår angrepet",
          "  Begge feiler -> ingenting skjer",
          "",
          "FIGHT BACK (opposed vs Fighting):",
          "  Angriper vinner -> full skade",
          "  Forsvarer vinner -> forsvarer gjør skade",
          "  Begge feiler -> ingenting skjer",
          "",
          "Dodge: 1 gratis per runde,",
          "  ekstra dodge koster handling neste runde.",
          "",
          "OUTNUMBERED:",
          "  Når forsvarer allerede har dodget",
          "  eller fought back denne runden:",
          "  -> alle etterfølgende angrep får",
          "     +1 bonus die.",
          "  Unntak: vesener med flere angrep/runde",
          "  kan dodge/fight back like mange ganger.",
          "  Gjelder IKKE skytevåpen.",
        ]),
        ("Skytevåpen", [
          "Rull Firearms-skill. INGEN opposed roll.",
          "Forsvarer kan KUN dodge ved point-blank.",
          "Ellers: bare dekke/bevege seg ut.",
          "",
          "Rekkevidde-modifikatorer:",
          "  Point-blank (\u2264 1/5 range): +1 bonus",
          "  Mellomdistanse (base range): normal",
          "  Lang (inntil 2x base): +1 penalty",
          "  Ekstrem (inntil 4x base): +2 penalty",
          "",
          "Andre modifikatorer:",
          "  Bevegelig mål: +1 penalty",
          "  Stort mål: +1 bonus",
          "  Smalt mål: +1 penalty",
          "  Sikte (bruker handling): +1 bonus",
          "",
          "Impale: Extreme suksess med",
          "  gjennomborende våpen",
          "  = maks våpenskade + ekstra kast.",
        ]),
        ("Manøvrer", [
          "Fighting-manøver (i stedet for skade):",
          "  Trip/knockdown: mål faller",
          "  Disarm: mål mister våpen",
          "  Hold/grapple: mål er fastholdt",
          "  Kaste: dytte/kaste motstanderen",
          "",
          "Krever: vinn opposed Fighting-sjekk.",
          "Build-differanse kan gi bonus/penalty:",
          "  Angriper Build \u2265 mål + 2: +1 bonus",
          "  Angriper Build \u2264 mål - 2: +1 penalty",
        ]),
        ("Damage Bonus (DB)", [
          "DB basert på STR + SIZ:",
          "  2\u201364:    -2",
          "  65\u201384:   -1",
          "  85\u2013124:  0",
          "  125\u2013164: +1d4",
          "  165\u2013204: +1d6",
          "  205\u2013284: +2d6",
          "  285\u2013364: +3d6",
          "",
          "Build-verdi:",
          "  DB -2: Build -2",
          "  DB -1: Build -1",
          "  DB 0:  Build 0",
          "  DB +1d4: Build 1",
          "  DB +1d6: Build 2",
          "  DB +2d6: Build 3",
        ]),
        ("Skade & heling", [
          "SKADENIVÅER:",
          "  Minor wound: tap < halve maks HP",
          "  Major wound: tap \u2265 halve maks HP",
          "",
          "MAJOR WOUND-konsekvenser:",
          "  CON-sjekk eller besvime",
          "  First Aid/Medicine innen 1 runde",
          "  Må stabiliseres ellers dør",
          "",
          "DYING (0 HP):",
          "  CON-sjekk per runde",
          "  Feil = død",
          "  Suksess = holder ut 1 runde til",
          "",
          "HELING:",
          "  First Aid: +1 HP (1 forsøk/skade)",
          "  Medicine: +1d3 HP (etter First Aid)",
          "  Naturlig: 1 HP/uke (minor)",
          "  Major wound: 1d3 HP/uke m/pleie",
        ]),
        ("Automatiske våpen", [
          "Burst: 3 kuler, +1 bonus die til skade.",
          "Full auto: velg antall mål,",
          "  fordel kuler, rull for hvert mål.",
          "  1 bonus die per 10 kuler på målet.",
          "",
          "Suppressive fire:",
          "  Dekker et område, alle i området",
          "  må Dodge eller ta 1 treff.",
          "  Bruker halve magasinet.",
        ]),
      ]),
      ("Sanity", "", [
        ("SAN-sjekk", [
          "Rull d100 \u2264 nåværende SAN.",
          "",
          "Format: 'X/Y'",
          "  Suksess: tap = X",
          "  Feil: tap = Y",
          "  Eks: '1/1d6' = suksess taper 1,",
          "    feil taper 1d6 SAN.",
          "",
          "Maks SAN = 99 \u2013 Cthulhu Mythos skill.",
          "",
          "SAN fumble: automatisk maks SAN-tap.",
        ]),
        ("Temporary Insanity", [
          "TRIGGER: 5+ SAN tapt i ETT kast.",
          "",
          "Keeper krever INT-sjekk:",
          "  INT suksess = investigator innser",
          "    sannheten -> MIDLERTIDIG GAL",
          "  INT feil = fortrengt minne,",
          "    investigator forblir ved sine fulle fem",
          "",
          "Midlertidig insanity varer 1d10 timer.",
          "Begynner med Bout of Madness.",
          "Etterfølges av Underlying Insanity.",
        ]),
        ("Bout of Madness", [
          "Oppstår ved midlertidig insanity.",
          "Keeper velger Real-Time eller Summary.",
          "",
          "REAL-TIME (varig 1d10 runder):",
          "  1: Amnesi (husker ingenting)",
          "  2: Psykosomatisk (blind/døv/lam)",
          "  3: Vold (angrip nærmeste)",
          "  4: Paranoia (alle er fiender)",
          "  5: Fysisk (kvalme/besvimelse)",
          "  6: Flukt (løp i panikk)",
          "  7: Hallusinasjoner",
          "  8: Ekko (gjenta handlinger meningsløst)",
          "  9: Fobi (ny eller eksisterende)",
          "  10: Katatoni (stivner helt)",
        ]),
        ("Summary (1d10 timer)", [
          "Etter real-time bout, varig effekt:",
          "  1: Amnesi for hele hendelsen",
          "  2: Tvangstanker / ritualer",
          "  3: Hallusinasjoner (vedvarende)",
          "  4: Irrasjonelt hat/frykt",
          "  5: Fobi (spesifikk, ny eller forsterket)",
          "  6: Mani (kompulsiv adferd)",
          "  7: Paranoia (stoler på ingen)",
          "  8: Dissosiasjon (fjern, uvirkelig)",
          "  9: Spiseforstyrrelse / søvnløshet",
          "  10: Mythos-besettelse (studerer forbudt)",
        ]),
        ("Fobier (utvalg)", [
          "Acrophobia \u2013 høydefobi",
          "Agoraphobia \u2013 åpne plasser",
          "Arachnophobia \u2013 edderkopper",
          "Claustrophobia \u2013 trange rom",
          "Demophobia \u2013 folkemengder",
          "Hemophobia \u2013 blod",
          "Hydrophobia \u2013 vann",
          "Mysophobia \u2013 smitte/skitt",
          "Necrophobia \u2013 døde/lik",
          "Nyctophobia \u2013 mørke",
          "Pyrophobia \u2013 ild",
          "Thalassophobia \u2013 havet/dypt vann",
          "Xenophobia \u2013 fremmede/ukjente",
          "Zoophobia \u2013 dyr",
        ]),
        ("Manier (utvalg)", [
          "Dipsomania \u2013 trang til alkohol",
          "Kleptomania \u2013 trang til å stjele",
          "Megalomania \u2013 storhetstanker",
          "Mythomania \u2013 tvangsløgner",
          "Necromania \u2013 besettelse med døden",
          "Pyromania \u2013 brannstifting",
          "Thanatomania \u2013 dødslengsel",
          "Xenomania \u2013 besettelse med fremmede",
        ]),
        ("Indefinite Insanity", [
          "Trigges når investigator har tapt",
          "  1/5 av nåværende SAN totalt.",
          "",
          "Effekt: langvarig galskap.",
          "  Spiller mister kontroll over karakter.",
          "  Keeper bestemmer adferd.",
          "  Varer måneder/år.",
          "",
          "Behandling:",
          "  Institusjonalisering",
          "  Psychoanalysis over tid",
          "  +1d3 SAN per måned (maks)",
          "  Mislykket behandling: -1d6 SAN",
        ]),
        ("SAN-gjenoppretting", [
          "Psychoanalysis: +1d3 SAN (1/måned)",
          "  Mislykket: -1d6 SAN!",
          "Self-help: forbedre skill = +1d3 SAN",
          "Fullføre scenario: Keeper-belønning",
          "",
          "Maks SAN = 99 \u2013 Cthulhu Mythos skill.",
          "Permanent SAN-tap kan ikke gjenopprettes",
          "  utover denne grensen.",
        ]),
      ]),
      ("Forfølgelse", "", [
        ("Oppsett", [
          "1. Type: fot eller kjøretøy.",
          "2. Antall locations: 5\u201310 (Keeper velger).",
          "3. Deltakere:",
          "   Fot: MOV basert på DEX, STR, SIZ.",
          "   Bil: speed-rating.",
          "4. Speed Roll (CON-sjekk):",
          "   Extreme suksess: +1 MOV for chasen",
          "   Suksess: ingen endring",
          "   Feil: -1 MOV for chasen",
          "   (kjøretøy: Drive Auto i stedet)",
          "5. Sammenlign MOV: høyere MOV flykter",
          "   umiddelbart. Ellers -> full chase.",
          "6. Sett startposisjoner på tracken.",
          "7. Plasser barrierer/farer på locations.",
          "",
          "MOV (Movement Rate):",
          "  Hvis DEX & STR begge > SIZ: MOV 9",
          "  Hvis enten DEX eller STR > SIZ: MOV 8",
          "  Hvis begge \u2264 SIZ: MOV 7",
          "  Alder 40\u201349: MOV -1",
          "  Alder 50\u201359: MOV -2 (etc.)",
        ]),
        ("Bevegelse & handlinger", [
          "Runder i DEX-rekkefølge (høy først).",
          "",
          "Hver runde kan deltaker:",
          "  - Bevege seg (MOV locations)",
          "  - Utføre 1 handling:",
          "    Speed: CON-sjekk for +1 location",
          "    Angrep: Fighting/Firearms",
          "    Barriere: skill-sjekk for å passere",
          "    Hinder: lag barriere for forfølger",
          "",
          "Hazard-handling koster handling OG",
          "  bevegelse den runden.",
        ]),
        ("Barrierer", [
          "Keeper plasserer barrierer på locations.",
          "Skill-sjekk for å passere:",
          "",
          "  Hopp over gjerde: Jump / Climb",
          "  Trang passasje: DEX / Dodge",
          "  Folkemengde: STR / Charm / Intimidate",
          "  Gjørme/glatt: DEX / Luck",
          "  Låst dør: Locksmith / STR",
          "  Trafikkert gate: Drive Auto / DEX",
          "",
          "Feil: mist 1 location bevegelse.",
          "Fumble: fall, skade, fastklemt, etc.",
        ]),
        ("Seier & tap", [
          "FLUKT lykkes når:",
          "  Avstand mellom = antall locations + 1",
          "  (forfølger kan ikke se målet).",
          "",
          "FANGET når:",
          "  Forfølger er på SAMME location.",
          "  Kamp eller interaksjon kan begynne.",
          "",
          "UTMATTELSE:",
          "  CON-sjekk per runde etter runde 5.",
          "  Feil: MOV reduseres med 1.",
          "  MOV 0: kan ikke bevege seg.",
        ]),
      ]),
      ("Magi & Tomer", "", [
        ("Besvergelse", [
          "Kostnader varierer per spell:",
          "  Magic Points (MP): vanligst",
          "  SAN: nesten alltid",
          "  HP: noen kraftige spells",
          "  POW: permanent offer (sjeldent)",
          "",
          "Casting time: 1 runde til flere timer.",
          "Noen krever komponenter/ritualer.",
          "",
          "MP regenereres: 1 per 2 timer hvile.",
          "MP = 0: bevisstløs i 1d8 timer.",
          "POW-offer: permanent, gjenopprettes IKKE.",
        ]),
        ("Mythos-tomer", [
          "Lesing av Mythos-tome:",
          "  Initial reading: uker til måneder",
          "  Full study: måneder til år",
          "",
          "Belønning: +Cthulhu Mythos skill.",
          "Kostnad: SAN-tap (varierer per tome).",
          "Kan også lære spells fra tomen.",
          "",
          "EKSEMPLER (CM-gevinst / SAN-tap):",
          "  Necronomicon (latin): +15 / -2d10",
          "  Necronomicon (original): +22 / -3d10",
          "  De Vermis Mysteriis: +10 / -1d8",
          "  Book of Eibon: +11 / -2d4",
          "  Cultes des Goules: +9 / -1d8",
          "  Pnakotiske man.: +7 / -1d6",
          "  Unaussprechlichen Kulten: +9 / -2d4",
          "  Revelations of Glaaki: +7 / -1d4",
          "  Book of Dzyan: +5 / -1d4",
        ]),
        ("Mythos-vesener (SAN)", [
          "Vesen: suksess / feil SAN-tap",
          "",
          "  Byakhee: 1/1d6",
          "  Dark Young: 0/1d8",
          "  Deep One: 0/1d6",
          "  Elder Thing: 1/1d6",
          "  Flying Polyp: 1d3/1d20",
          "  Ghoul: 0/1d6",
          "  Great Race: 0/1d6",
          "  Hound of Tindalos: 1d3/1d20",
          "  Mi-Go: 0/1d6",
          "  Nightgaunt: 0/1d6",
          "  Shoggoth: 1d6/1d20",
          "  Star Spawn: 1d6/1d20",
          "  Star Vampire: 1/1d8",
          "",
          "  Great Old Ones:",
          "  Cthulhu: 1d10/1d100",
          "  Hastur: 1d10/1d100",
          "  Nyarlathotep: 0/1d10 (varierer)",
          "  Yog-Sothoth: 1d10/1d100",
        ]),
      ]),
      ("Pulp Cthulhu", "", [
        ("Pulp-regler", [
          "Helter er TØFFERE enn standard CoC.",
          "",
          "HP: (CON + SIZ) / 5 (avrundet ned)",
          "  Standard CoC: (CON+SIZ) / 10",
          "  Effektivt DOBBEL HP.",
          "  Valgfritt lavnivå: (CON+SIZ)/10",
          "",
          "Luck: 2d6+6 x 5 (høyere enn standard)",
          "  Standard CoC: 3d6 x 5",
          "  Regenerer 2d10 Luck per sesjon.",
          "",
          "First Aid: +1d4 HP (standard: +1 HP)",
          "  Extreme suksess: automatisk 4 HP.",
          "Medicine: +1d4 HP (standard: +1d3)",
          "",
          "Pulp Talents: 2 stk (standard).",
          "  Lavnivå pulp: 1 talent",
          "  Høynivå pulp: 3 talents",
          "",
          "Kampkast kan IKKE pushes (som standard).",
          "Spending Luck: kan også brukes til:",
          "  - Unngå dying (5 Luck = stabiliser)",
          "  - Redusere skade (etter kast)",
        ]),
        ("Arketyper", [
          "Velg 1 arketype ved opprettelse.",
          "Gir bonuser og Pulp Talents.",
          "",
          "  Adventurer: allsidig eventyrer",
          "  Beefcake: fysisk sterk, ekstra HP",
          "  Bon Vivant: sjarmerende, sosialt dyktig",
          "  Cold Blooded: hensynsløs, presist",
          "  Dreamer: kreativ, Mythos-sensitiv",
          "  Egghead: intellektuell, kunnskapsrik",
          "  Explorer: utforsker, overlevelse",
          "  Femme/Homme Fatale: forførende",
          "  Grease Monkey: mekaniker, oppfinnsom",
          "  Hard Boiled: tøff, utholdende",
          "  Harlequin: entertainer, distraherende",
          "  Hunter: jeger, naturkyndig",
          "  Mystic: spirituell, spådomsevne",
          "  Outsider: ensom, selvlært",
          "  Reckless: våghals, risikotaker",
          "  Sidekick: lojal, støttende",
          "  Swashbuckler: akrobatisk fighter",
          "  Thrill Seeker: adrenalinjansen",
          "  Two-Fisted: nevekamp-spesialist",
        ]),
        ("Pulp Talents (utvalg)", [
          "FYSISK:",
          "  Brawler: +1d6 melee-skade",
          "  Iron Jaw: ignorer 1 K.O. per sesjon",
          "  Quick Healer: dobbel heling",
          "  Tough Guy: +1d6 ekstra HP",
          "",
          "MENTAL:",
          "  Arcane Insight: +2 Cthulhu Mythos",
          "  Gadget: lag improvisert gjenstand",
          "  Photographic Memory: husk alt",
          "  Psychic Power: sjette sans",
          "",
          "SOSIAL:",
          "  Smooth Talker: re-roll 1 sosial sjekk",
          "  Master of Disguise: +1 bonus Disguise",
          "  Lucky: +1d10 ekstra Luck-regen",
          "",
          "KAMP:",
          "  Rapid Fire: ekstra skudd uten penalty",
          "  Outmaneuver: +1 bonus på manøvrer",
          "  Fleet Footed: +1 MOV i chase",
        ]),
      ]),
      ("Tabeller", "", [
        ("Våpentabell \u2013 melee", [
          "Våpen: skade / attacks",
          "",
          "  Unarmed (knytneve): 1d3+DB / 1",
          "  Head butt: 1d4+DB / 1",
          "  Kick: 1d4+DB / 1",
          "  Grapple: special / 1",
          "  Kniv (liten): 1d4+DB / 1",
          "  Kniv (stor): 1d6+DB / 1",
          "  Klubbe/kølle: 1d8+DB / 1",
          "  Sverd/sabel: 1d8+DB / 1",
          "  Øks (stor): 1d8+2+DB / 1",
          "  Spyd: 1d8+1+DB / 1",
          "  Motorsag: 2d8 / 1",
        ]),
        ("Våpentabell \u2013 skytevåpen", [
          "Våpen: skade / range / shots",
          "",
          "  Derringer (.41): 1d8 / 10y / 1",
          "  Revolver (.32): 1d8 / 15y / 6",
          "  Revolver (.45): 1d10+2 / 15y / 6",
          "  Pistol (9mm): 1d10 / 15y / 8",
          "  Pistol (.45 auto): 1d10+2 / 15y / 7",
          "  Rifle (.30): 2d6+4 / 110y / 5",
          "  Rifle (.303): 2d6+4 / 110y / 10",
          "  Shotgun (12g): 4d6/2d6/1d6",
          "    (range: 10/20/50 yard)",
          "  Thompson SMG: 1d10+2 / 20y / 20",
          "  Dynamitt: 5d6 / thrown / 1",
          "    (radius 5 yard)",
        ]),
        ("SAN-tap oversikt", [
          "HENDELSE: suksess / feil",
          "",
          "  Se et lik: 0/1d3",
          "  Se en venn dø: 0/1d4",
          "  Se noe uforklarlig: 0/1d2",
          "  Se et grusomt drap: 1/1d4+1",
          "  Se massedrap: 1d3/1d6+1",
          "  Finne en grusomhet: 0/1d3",
          "",
          "  Oppdage Mythos-bevis: 0/1d2",
          "  Lese Mythos-tome: 1/1d4",
          "  Se Mythos-ritual: 1/1d6",
          "  Bli utsatt for besvergelse: 1/1d6",
        ]),
        ("Alderseffekter", [
          "Alder påvirker stats ved opprettelse:",
          "",
          "  15\u201319: -5 SIZ/STR, -5 EDU,",
          "    Luck: rull 2x, bruk best",
          "  20\u201339: EDU-forbedring: +1",
          "  40\u201349: EDU +2, -5 fritt STR/CON/DEX,",
          "    APP -5, MOV -1",
          "  50\u201359: EDU +3, -10 fritt STR/CON/DEX,",
          "    APP -10, MOV -2",
          "  60\u201369: EDU +4, -20 fritt STR/CON/DEX,",
          "    APP -15, MOV -3",
          "  70\u201379: EDU +4, -40 fritt STR/CON/DEX,",
          "    APP -20, MOV -4",
          "  80\u201389: EDU +4, -80 fritt STR/CON/DEX,",
          "    APP -25, MOV -5",
        ]),
        ("Credit Rating", [
          "Credit Rating = formue/sosial status:",
          "",
          "  0: fattig, hjemløs",
          "  1\u20139: fattig, kun nødvendig",
          "  10\u201349: gjennomsnittlig",
          "  50\u201389: velstående",
          "  90\u201398: rik",
          "  99: enormt rik",
          "",
          "Spending level (per dag):",
          "  CR 0: $0.50",
          "  CR 1\u20139: $2",
          "  CR 10\u201349: $10",
          "  CR 50\u201389: $50",
          "  CR 90\u201398: $250",
          "  CR 99: $5000",
        ]),
      ]),
    ]


    def request_android_permissions():
        if platform != 'android':
            return
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([
                Permission.READ_EXTERNAL_STORAGE,
                Permission.READ_MEDIA_IMAGES,
                Permission.READ_MEDIA_AUDIO,
                Permission.INTERNET,
                Permission.ACCESS_NETWORK_STATE,
                Permission.ACCESS_WIFI_STATE,
                Permission.CHANGE_WIFI_MULTICAST_STATE
            ])
        except:
            pass

    def load_json(p, d=None):
        try:
            with open(p, 'r') as f:
                return json.load(f)
        except:
            return d if d is not None else []

    def save_json(p, d):
        try:
            with open(p, 'w') as f:
                json.dump(d, f, indent=2, ensure_ascii=False)
        except:
            pass

    # === HJELPEFUNKSJONER ===

    def mkbtn(text, cb=None, accent=False, danger=False, small=False, **kw):
        c = GOLD if accent else (RED if danger else TXT)
        b = RBtn(text=text, color=c, bg_color=BTN,
                 font_size=sp(11) if small else sp(13), **kw)
        if cb:
            b.bind(on_release=lambda x: cb())
        return b

    def mklbl(text, color=TXT, size=12, bold=False, h=None, wrap=False):
        kw = {'text': text, 'font_size': sp(size), 'color': color, 'bold': bold}
        if h:
            kw['size_hint_y'] = None
            kw['height'] = dp(h)
        l = Label(**kw)
        if wrap:
            l.halign = 'left'
            l.size_hint_y = None
            # Bind text_size til label-bredden slik at det tilpasser seg rotasjon
            l.bind(width=lambda w, v: setattr(w, 'text_size', (v - dp(8), None)))
            l.bind(texture_size=l.setter('size'))
        return l

    def mksep(h=6):
        return Widget(size_hint_y=None, height=dp(h))

    def mkvol(callback, value=0.7):
        vr = BoxLayout(size_hint_y=None, height=dp(32), padding=[dp(10), 0])
        vr.add_widget(Label(text="Vol", color=DIM, size_hint_x=0.08, font_size=sp(10)))
        sl = Slider(min=0, max=1, value=value, size_hint_x=0.92)
        sl.bind(value=lambda s, v: callback(v))
        vr.add_widget(sl)
        return vr

    # === SERVER / CAST / PLAYERS ===
    class QuietHandler(SimpleHTTPRequestHandler):
        def log_message(self, f, *a):
            pass

    class MediaServer:
        def __init__(self):
            self._h = None
        def start(self):
            if self._h:
                return
            try:
                h = partial(QuietHandler, directory=BASE_DIR)
                self._h = HTTPServer(('0.0.0.0', HTTP_PORT), h)
                threading.Thread(target=self._h.serve_forever, daemon=True).start()
            except:
                pass
        def stop(self):
            if self._h:
                self._h.shutdown()
                self._h = None
        @staticmethod
        def ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                r = s.getsockname()[0]
                s.close()
                return r
            except:
                return "127.0.0.1"
        def url(self, fp):
            return f"http://{self.ip()}:{HTTP_PORT}/{os.path.relpath(fp, BASE_DIR)}"

    class CastMgr:
        def __init__(self):
            self.devices = {}
            self.cc = None
            self.mc = None
            self._br = None
        def scan(self, cb=None):
            if not CAST_AVAILABLE:
                return
            self.devices = {}
            def _s():
                try:
                    ccs, br = pychromecast.get_chromecasts()
                    self._br = br
                except:
                    ccs = []
                for c in ccs:
                    self.devices[c.cast_info.friendly_name] = c
                if cb:
                    Clock.schedule_once(lambda dt: cb(list(self.devices.keys())), 0)
            threading.Thread(target=_s, daemon=True).start()
        def connect(self, name, cb=None):
            if name not in self.devices:
                return
            def _c():
                try:
                    c = self.devices[name]
                    c.wait()
                    self.cc = c
                    self.mc = c.media_controller
                    ok = True
                except:
                    ok = False
                if cb:
                    Clock.schedule_once(lambda dt: cb(ok), 0)
            threading.Thread(target=_c, daemon=True).start()
        def cast_img(self, url, cb=None):
            if not self.mc:
                return
            def _c():
                try:
                    self.mc.play_media(url, 'image/jpeg')
                    self.mc.block_until_active()
                    ok = True
                except:
                    ok = False
                if cb:
                    Clock.schedule_once(lambda dt: cb(ok), 0)
            threading.Thread(target=_c, daemon=True).start()
        def disconnect(self):
            try:
                if self._br:
                    self._br.stop_discovery()
                if self.cc:
                    self.cc.disconnect()
            except:
                pass
            self.cc = None
            self.mc = None

    class APlayer:
        def __init__(self):
            self.mp = None
            self.is_playing = False
            self._v = 0.7
        def play(self, path):
            self.stop()
            try:
                self.mp = MediaPlayer()
                self.mp.setDataSource(path)
                self.mp.setVolume(self._v, self._v)
                self.mp.prepare()
                self.mp.start()
                self.is_playing = True
            except:
                self.mp = None
                self.is_playing = False
        def stop(self):
            if self.mp:
                try:
                    if self.mp.isPlaying():
                        self.mp.stop()
                    self.mp.release()
                except:
                    pass
                self.mp = None
            self.is_playing = False
        def pause(self):
            if self.mp and self.is_playing:
                try:
                    self.mp.pause()
                    self.is_playing = False
                except:
                    pass
        def resume(self):
            if self.mp and not self.is_playing:
                try:
                    self.mp.start()
                    self.is_playing = True
                except:
                    pass
        def vol(self, v):
            self._v = v
            if self.mp:
                try:
                    self.mp.setVolume(v, v)
                except:
                    pass

    class SPlayer:
        def __init__(self):
            self.mp = None
            self.is_playing = False
            self._v = 0.5
        def play_url(self, url):
            self.stop()
            if not USE_JNIUS:
                return False
            def _s():
                try:
                    self.mp = MediaPlayer()
                    self.mp.setDataSource(url)
                    self.mp.setVolume(self._v, self._v)
                    self.mp.prepare()
                    self.mp.start()
                    self.is_playing = True
                    log("Stream OK")
                except Exception as e:
                    log(f"Stream err: {e}")
                    if self.mp:
                        try: self.mp.release()
                        except: pass
                        self.mp = None
                    self.is_playing = False
            threading.Thread(target=_s, daemon=True).start()
            return True
        def stop(self):
            if self.mp:
                try:
                    if self.mp.isPlaying():
                        self.mp.stop()
                    self.mp.release()
                except:
                    pass
                self.mp = None
            self.is_playing = False
        def vol(self, v):
            self._v = v
            if self.mp:
                try:
                    self.mp.setVolume(v, v)
                except:
                    pass

    class FPlayer:
        def __init__(self):
            from kivy.core.audio import SoundLoader
            self.SL = SoundLoader
            self.snd = None
            self.is_playing = False
            self._v = 0.7
        def play(self, path):
            self.stop()
            self.snd = self.SL.load(path)
            if self.snd:
                self.snd.volume = self._v
                self.snd.play()
                self.is_playing = True
        def stop(self):
            if self.snd:
                try: self.snd.stop()
                except: pass
                self.snd = None
            self.is_playing = False
        def pause(self):
            if self.snd and self.is_playing:
                self.snd.stop()
                self.is_playing = False
        def resume(self):
            if self.snd and not self.is_playing:
                self.snd.play()
                self.is_playing = True
        def vol(self, v):
            self._v = v
            if self.snd:
                self.snd.volume = v

    # ============================================================
    class CampaignForgeApp(App):
        def build(self):
            log("=== BUILD (CampaignForge v0.1.0) ===")
            Window.clearcolor = BG
            self.title = "CampaignForge"
            self.tracks = []
            self.ct = -1
            self.sel_img = None
            self.auto_cast = True
            self.cur_folder = IMG_DIR
            self.player = APlayer() if USE_JNIUS else FPlayer()
            self.streamer = SPlayer()
            self.cast = CastMgr()
            self.server = MediaServer()
            self.chars = load_json(CHAR_FILE, [])
            self.edit_idx = None

            # FloatLayout som rot – lar oss legge splash oppå
            wrapper = FloatLayout()

            main = BoxLayout(orientation='vertical', spacing=0,
                             size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            main.add_widget(Widget(size_hint_y=None, height=dp(30)))

            # FANER
            tabs = RBox(size_hint_y=None, height=dp(52), spacing=dp(4),
                        padding=[dp(8), 0], bg_color=BTN)
            self._tabs = {}
            for key, txt in [('img','Bilder'),('mus','Musikk'),('amb','Ambient'),('tool','Karakter'),('rules','Regler'),('cast','Cast')]:
                active = key == 'img'
                b = RToggle(text=txt, group='tabs',
                            state='down' if active else 'normal',
                            bg_color=BTNH if active else BTN,
                            color=GOLD if active else DIM,
                            font_size=sp(11))
                b.bind(state=self._tab_color)
                b.bind(on_release=lambda x, k=key: self._tab(k))
                tabs.add_widget(b)
                self._tabs[key] = b
            main.add_widget(tabs)

            # HOVEDINNHOLD
            self.content = RBox(bg_color=BG2)
            main.add_widget(self.content)

            # MINI-PLAYER
            mp = RBox(size_hint_y=None, height=dp(48), spacing=dp(6),
                      padding=[dp(10), dp(4)], bg_color=BTN)
            mp.add_widget(Widget(size_hint_x=None, width=dp(4)))
            self.mp_lbl = Label(text="Ingen musikk", font_size=sp(11),
                                color=DIM, size_hint_x=0.45, halign='left')
            self.mp_lbl.bind(size=self.mp_lbl.setter('text_size'))
            mp.add_widget(self.mp_lbl)
            for t, cb in [("<<", self.prev_track), (">>", self.next_track)]:
                mp.add_widget(mkbtn(t, cb, small=True, size_hint_x=None, width=dp(44)))
            self.mp_btn = mkbtn("Play", self.toggle_play, accent=True,
                                small=True, size_hint_x=None, width=dp(60))
            mp.add_widget(self.mp_btn)
            main.add_widget(mp)

            self.status = Label(text="", font_size=sp(10), color=DIM,
                                size_hint_y=None, height=dp(20))
            main.add_widget(self.status)

            wrapper.add_widget(main)

            # === SPLASH SCREEN ===
            self.splash = RBox(bg_color=BG, radius=0,
                               orientation='vertical',
                               size_hint=(1, 1),
                               pos_hint={'x': 0, 'y': 0})
            # Sentrert innhold
            self.splash.add_widget(Widget())  # fyll topp
            t1 = Label(text="CAMPAIGN", font_size=sp(42), color=GOLD,
                       bold=True, size_hint_y=None, height=dp(60),
                       halign='center')
            t1.bind(size=t1.setter('text_size'))
            self.splash.add_widget(t1)
            t2 = Label(text="FORGE", font_size=sp(42), color=GDIM,
                       bold=True, size_hint_y=None, height=dp(60),
                       halign='center')
            t2.bind(size=t2.setter('text_size'))
            self.splash.add_widget(t2)
            sub = Label(text="Dungeon Master's Companion", font_size=sp(13),
                        color=DIM, size_hint_y=None, height=dp(30),
                        halign='center')
            sub.bind(size=sub.setter('text_size'))
            self.splash.add_widget(sub)
            self.splash.add_widget(Widget())  # fyll bunn
            wrapper.add_widget(self.splash)

            self._tab('img')
            log("UI built OK")
            Clock.schedule_once(lambda dt: request_android_permissions(), 0.5)
            Clock.schedule_once(lambda dt: self._init(), 3)
            # Fade ut splash etter 2.5 sek
            Clock.schedule_once(self._dismiss_splash, 2.5)
            return wrapper

        def _dismiss_splash(self, dt):
            if self.splash:
                anim = Animation(opacity=0, duration=0.8)
                def _remove(*a):
                    if self.splash.parent:
                        self.splash.parent.remove_widget(self.splash)
                    self.splash = None
                anim.bind(on_complete=_remove)
                anim.start(self.splash)

        def _tab_color(self, btn, state):
            if state == 'down':
                btn.bg_color = BTNH
                btn.color = GOLD
            else:
                btn.bg_color = BTN
                btn.color = DIM

        def _init(self):
            ensure_dirs()
            self.server.start()
            self._load_imgs()
            self._load_tracks()
            self.status.text = f"IP: {MediaServer.ip()}  |  Cast: {'Ja' if CAST_AVAILABLE else 'Nei'}"

        def _tab(self, k):
            self.content.clear_widgets()
            builders = {
                'img': self._mk_img, 'mus': self._mk_mus,
                'amb': self._mk_amb, 'tool': self._mk_tool,
                'rules': self._mk_rules, 'cast': self._mk_cast,
            }
            if k in builders:
                self.content.add_widget(builders[k]())

        # ---------- BILDER ----------
        def _mk_img(self):
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            # Svart bakgrunn bak preview-bildet
            preview_box = RBox(size_hint_y=0.4, bg_color=BLK, radius=dp(12))
            self.preview = Image(allow_stretch=True, keep_ratio=True,
                                 color=[1, 1, 1, 0] if not self.sel_img else [1, 1, 1, 1])
            if self.sel_img:
                self.preview.source = self.sel_img
            preview_box.add_widget(self.preview)
            p.add_widget(preview_box)
            p.add_widget(Label(text="CAMPAIGN FORGE", font_size=sp(18), color=GDIM,
                               bold=True, size_hint_y=None, height=dp(28)))
            self.img_lbl = Label(text="", font_size=sp(12), color=DIM,
                                 size_hint_y=None, height=dp(20))
            p.add_widget(self.img_lbl)
            nav = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6), padding=[dp(6), 0])
            self.path_lbl = Label(text="", font_size=sp(10), color=DIM, size_hint_x=0.35)
            nav.add_widget(self.path_lbl)
            nav.add_widget(mkbtn("Opp", self.folder_up, small=True, size_hint_x=0.2))
            self.ac_btn = mkbtn("AC:PA", self._toggle_ac, accent=True, small=True, size_hint_x=0.25)
            nav.add_widget(self.ac_btn)
            nav.add_widget(mkbtn("Oppdater", self._load_imgs, small=True, size_hint_x=0.2))
            p.add_widget(nav)
            scroll = ScrollView(size_hint_y=0.4)
            self.img_grid = GridLayout(cols=3, spacing=dp(6), padding=dp(6), size_hint_y=None)
            self.img_grid.bind(minimum_height=self.img_grid.setter('height'))
            scroll.add_widget(self.img_grid)
            p.add_widget(scroll)
            self._load_imgs()
            return p

        def _load_imgs(self):
            if not hasattr(self, 'img_grid'):
                return
            self.img_grid.clear_widgets()
            f = self.cur_folder
            rel = os.path.relpath(f, IMG_DIR) if f != IMG_DIR else ""
            self.path_lbl.text = f"/{rel}" if rel else "/"
            try:
                if not os.path.exists(f):
                    self.img_lbl.text = "Mappe ikke funnet"
                    self.img_grid.add_widget(
                        mklbl("Mappen finnes ikke ennå.\n"
                              "Start appen på nytt etter å ha\n"
                              "godtatt tillatelser.",
                              color=DIM, size=11, wrap=True))
                    return
                items = sorted(os.listdir(f))
                dirs = [d for d in items if os.path.isdir(os.path.join(f, d)) and not d.startswith('.')]
                imgs = [x for x in items if x.lower().endswith(IMG_EXT)]
                self.img_lbl.text = f"{len(dirs)} mapper, {len(imgs)} bilder"
                if not dirs and not imgs:
                    self.img_grid.add_widget(
                        mklbl("Ingen bilder funnet.\n\n"
                              "Legg bilder i:\n"
                              "Dokumenter/CampaignForge/images/\n\n"
                              "Tips: lag undermapper for\n"
                              "å organisere etter scenario,\n"
                              "f.eks. images/Slow Boat/\n\n"
                              "Støttede formater:\n"
                              ".png  .jpg  .jpeg  .webp",
                              color=DIM, size=11, wrap=True))
                    return
                for d in dirs:
                    self.img_grid.add_widget(
                        mkbtn(f"[{d}]", lambda dn=d: self._enter(dn),
                              accent=True, small=True, size_hint_y=None, height=dp(70)))
                for fn in imgs:
                    path = os.path.join(f, fn)
                    img = Image(source=path, allow_stretch=True, keep_ratio=True,
                                size_hint_y=None, height=dp(100), mipmap=True)
                    img._path = path
                    img.bind(on_touch_down=self._img_touch)
                    self.img_grid.add_widget(img)
            except Exception as e:
                log(f"load_imgs: {e}")

        def _img_touch(self, w, touch):
            if w.collide_point(*touch.pos):
                self._sel_img(w._path)
                return True
            return False

        def _enter(self, name):
            self.cur_folder = os.path.join(self.cur_folder, name)
            self._load_imgs()

        def folder_up(self):
            if self.cur_folder != IMG_DIR:
                self.cur_folder = os.path.dirname(self.cur_folder)
                self._load_imgs()

        def _sel_img(self, path):
            self.sel_img = path
            self.img_lbl.text = os.path.basename(path)
            self.img_lbl.color = GOLD
            Animation.cancel_all(self.preview, 'opacity')
            fade_out = Animation(opacity=0, duration=0.3)
            def _swap(*a):
                self.preview.source = path
                Animation(opacity=1, duration=0.4).start(self.preview)
                if self.auto_cast and self.cast.mc:
                    self.img_lbl.text = "Caster..."
                    self.cast.cast_img(self.server.url(path),
                                       cb=lambda ok: setattr(self.img_lbl, 'text',
                                                             "Castet!" if ok else "Feilet"))
            fade_out.bind(on_complete=_swap)
            self.preview.color = [1, 1, 1, 1]
            fade_out.start(self.preview)

        def _toggle_ac(self):
            self.auto_cast = not self.auto_cast
            self.ac_btn.text = f"AC:{'PA' if self.auto_cast else 'AV'}"

        # ---------- MUSIKK ----------
        def _mk_mus(self):
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            self.trk_lbl = Label(text="Velg et spor", font_size=sp(14), color=DIM,
                                 size_hint_y=None, height=dp(34), bold=True)
            p.add_widget(self.trk_lbl)
            ctrl = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            ctrl.add_widget(mkbtn("<<", self.prev_track, small=True))
            ctrl.add_widget(mkbtn("Play", self.toggle_play, accent=True))
            ctrl.add_widget(mkbtn(">>", self.next_track, small=True))
            ctrl.add_widget(mkbtn("Stopp", self.stop_music, danger=True, small=True))
            p.add_widget(ctrl)
            p.add_widget(mkvol(self.player.vol, 0.7))
            scroll = ScrollView()
            self.trk_grid = GridLayout(cols=1, spacing=dp(4), padding=dp(6), size_hint_y=None)
            self.trk_grid.bind(minimum_height=self.trk_grid.setter('height'))
            scroll.add_widget(self.trk_grid)
            p.add_widget(scroll)
            self._load_tracks()
            return p

        def _load_tracks(self):
            if not hasattr(self, 'trk_grid'):
                return
            self.trk_grid.clear_widgets()
            self.tracks = []
            try:
                if not os.path.exists(MUSIC_DIR):
                    self.trk_lbl.text = "Mappe ikke funnet"
                    self.trk_grid.add_widget(
                        mklbl("Musikkmappen finnes ikke ennå.\n"
                              "Start appen på nytt etter å ha\n"
                              "godtatt tillatelser.",
                              color=DIM, size=11, wrap=True))
                    return
                fl = sorted([f for f in os.listdir(MUSIC_DIR)
                             if f.lower().endswith(('.mp3','.ogg','.wav','.flac'))])
                self.trk_lbl.text = f"{len(fl)} spor"
                if not fl:
                    self.trk_grid.add_widget(
                        mklbl("Ingen musikkfiler funnet.\n\n"
                              "Legg lydfiler i:\n"
                              "Dokumenter/CampaignForge/music/\n\n"
                              "Støttede formater:\n"
                              ".mp3  .ogg  .wav  .flac",
                              color=DIM, size=11, wrap=True))
                    return
                for i, fn in enumerate(fl):
                    self.tracks.append(os.path.join(MUSIC_DIR, fn))
                    self.trk_grid.add_widget(
                        mkbtn(fn, lambda idx=i: self.play_track(idx),
                              small=True, size_hint_y=None, height=dp(42)))
            except Exception as e:
                log(f"load_tracks: {e}")

        def play_track(self, idx):
            if idx < 0 or idx >= len(self.tracks):
                return
            self.ct = idx
            self.player.play(self.tracks[idx])
            n = os.path.basename(self.tracks[idx])
            self.trk_lbl.text = f"Spiller: {n}"
            self.trk_lbl.color = GOLD
            self.mp_lbl.text = n
            self.mp_btn.text = "Pause"

        def toggle_play(self):
            if not self.player.is_playing and self.ct < 0:
                if self.tracks:
                    self.play_track(0)
                return
            if self.player.is_playing:
                self.player.pause()
                self.mp_btn.text = "Play"
            else:
                self.player.resume()
                self.mp_btn.text = "Pause"

        def stop_music(self):
            self.player.stop()
            self.mp_btn.text = "Play"
            self.mp_lbl.text = "Stoppet"
            self.trk_lbl.text = "Stoppet"

        def next_track(self):
            if self.tracks:
                self.play_track((self.ct + 1) % len(self.tracks))

        def prev_track(self):
            if self.tracks:
                self.play_track((self.ct - 1) % len(self.tracks))

        # ---------- AMBIENT ----------
        def _mk_amb(self):
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(6), size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))
            for snd in AMBIENT_SOUNDS:
                if 'url' not in snd:
                    g.add_widget(mklbl(snd['name'], color=GDIM, size=11, bold=True, h=24))
                else:
                    g.add_widget(
                        mkbtn(snd['name'],
                              lambda u=snd['url'], n=snd['name']: self._pa(u, n),
                              small=True, size_hint_y=None, height=dp(40)))
            scroll.add_widget(g)
            p.add_widget(scroll)
            p.add_widget(mkbtn("Stopp ambient", self._sa, danger=True,
                               size_hint_y=None, height=dp(44)))
            p.add_widget(mkvol(self.streamer.vol, 0.5))
            self.amb_lbl = mklbl("", color=DIM, size=11, h=20)
            p.add_widget(self.amb_lbl)
            p.add_widget(Widget(size_hint_y=1))
            return p

        def _pa(self, url, name):
            self._an = name
            self._ac = 0
            self.amb_lbl.text = f"Laster: {name}..."
            if self.streamer.play_url(url):
                Clock.schedule_interval(self._poll, 2)

        def _poll(self, dt):
            self._ac += 1
            if self.streamer.is_playing:
                self.amb_lbl.text = f"Spiller: {self._an}"
                self.amb_lbl.color = GRN
                return False
            if self._ac >= 10:
                self.amb_lbl.text = f"Feilet: {self._an}"
                self.amb_lbl.color = RED
                return False
            self.amb_lbl.text = f"Laster: {self._an} ({self._ac*2}s)..."
            return True

        def _sa(self):
            self.streamer.stop()
            self.amb_lbl.text = "Stoppet"
            self.amb_lbl.color = DIM

        # ---------- REGLER ----------
        def _mk_rules(self):
            """Sammenleggbar mappe-visning med overlay for innhold."""
            p = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(4))
            self._rules_expanded = set()
            self._rules_overlay = None

            # Header
            hdr = BoxLayout(size_hint_y=None, height=dp(34))
            hdr.add_widget(mklbl("REGLER & REFERANSE", color=GOLD, size=15, bold=True))
            p.add_widget(hdr)
            p.add_widget(mksep(2))

            # Mappe-liste
            scroll = ScrollView()
            self._rules_tree = GridLayout(cols=1, spacing=dp(2), padding=dp(4), size_hint_y=None)
            self._rules_tree.bind(minimum_height=self._rules_tree.setter('height'))
            scroll.add_widget(self._rules_tree)
            p.add_widget(scroll)

            # Overlay-container (usynlig til innhold åpnes)
            self._rules_main = p
            self._rules_build_tree()
            return p

        def _rules_build_tree(self):
            """Bygg mappetreet med åpne/lukkede mapper."""
            self._rules_tree.clear_widgets()
            for i, (cat_name, icon, subs) in enumerate(RULES):
                expanded = i in self._rules_expanded
                arrow = "[-]" if expanded else "[+]"
                # Mappe-knapp
                fbtn = RBtn(
                    text=f"  {arrow}  {cat_name}",
                    bg_color=BTNH if expanded else BTN,
                    color=GOLD if expanded else TXT,
                    font_size=sp(13), halign='left',
                    size_hint_y=None, height=dp(44))
                fbtn.bind(on_release=lambda x, idx=i: self._rules_toggle(idx))
                self._rules_tree.add_widget(fbtn)

                if expanded:
                    for j, (sub_name, content) in enumerate(subs):
                        n = len([l for l in content if l])
                        sbtn = RBtn(
                            text=f"       >  {sub_name}",
                            bg_color=BG2, color=TXT,
                            font_size=sp(12), halign='left',
                            size_hint_y=None, height=dp(38))
                        sbtn.bind(on_release=lambda x, ci=i, si=j: self._rules_open(ci, si))
                        self._rules_tree.add_widget(sbtn)

        def _rules_toggle(self, cat_idx):
            """Åpne/lukke en mappe."""
            if cat_idx in self._rules_expanded:
                self._rules_expanded.discard(cat_idx)
            else:
                self._rules_expanded.add(cat_idx)
            self._rules_build_tree()

        def _rules_open(self, cat_idx, sub_idx):
            """Vis regelinnhold som overlay."""
            cat_name, icon, subs = RULES[cat_idx]
            sub_name, content = subs[sub_idx]

            # Fjern evt. eksisterende overlay
            self._rules_close_overlay()

            # Bygg overlay
            overlay = RBox(bg_color=BG, radius=dp(16),
                           orientation='vertical', spacing=dp(4),
                           padding=dp(8),
                           size_hint=(0.95, 0.92),
                           pos_hint={'center_x': 0.5, 'center_y': 0.5})

            # Header med lukk + navigering
            hdr = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
            hdr.add_widget(mkbtn("Lukk", self._rules_close_overlay,
                                 danger=True, small=True, size_hint_x=0.25))
            if sub_idx > 0:
                hdr.add_widget(mkbtn("<<",
                    lambda: (self._rules_close_overlay(), self._rules_open(cat_idx, sub_idx - 1)),
                    small=True, size_hint_x=None, width=dp(36)))
            else:
                hdr.add_widget(Widget(size_hint_x=None, width=dp(36)))

            hdr.add_widget(mklbl(sub_name, color=GOLD, size=13, bold=True))

            if sub_idx < len(subs) - 1:
                hdr.add_widget(mkbtn(">>",
                    lambda: (self._rules_close_overlay(), self._rules_open(cat_idx, sub_idx + 1)),
                    small=True, size_hint_x=None, width=dp(36)))
            else:
                hdr.add_widget(Widget(size_hint_x=None, width=dp(36)))
            overlay.add_widget(hdr)

            # Breadcrumb
            overlay.add_widget(mklbl(f"{cat_name}  >  {sub_name}",
                                     color=DIM, size=10, h=18))

            # Separator
            sep = Widget(size_hint_y=None, height=dp(1))
            from kivy.graphics import Color as GColor, Rectangle as GRect
            with sep.canvas:
                GColor(rgba=BTNH)
                r = GRect(pos=sep.pos, size=sep.size)
            sep.bind(pos=lambda w, v: setattr(r, 'pos', w.pos),
                     size=lambda w, v: setattr(r, 'size', w.size))
            overlay.add_widget(sep)
            overlay.add_widget(mksep(4))

            # Innhold
            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(1), padding=dp(6), size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            for line in content:
                if line == "":
                    g.add_widget(mksep(10))
                elif line.startswith("  "):
                    g.add_widget(mklbl(line, color=DIM, size=12, h=20))
                else:
                    g.add_widget(mklbl(line, color=TXT, size=13, h=22))

            g.add_widget(mksep(30))
            scroll.add_widget(g)
            overlay.add_widget(scroll)

            # Legg overlay over hele content-området
            # Bruk FloatLayout-wrapperen (root)
            root = self._rules_main
            while root.parent and not isinstance(root.parent, FloatLayout):
                root = root.parent
            fl = root.parent if isinstance(root.parent, FloatLayout) else root

            # Dimmet bakgrunn
            dim = Widget(size_hint=(1, 1))
            from kivy.graphics import Color as GC2, Rectangle as GR2
            with dim.canvas:
                GC2(rgba=[0, 0, 0, 0.6])
                dr = GR2(pos=dim.pos, size=dim.size)
            dim.bind(pos=lambda w, v: setattr(dr, 'pos', w.pos),
                     size=lambda w, v: setattr(dr, 'size', w.size))
            dim.bind(on_touch_down=lambda w, t: self._rules_close_overlay() or True)

            self._rules_dim = dim
            self._rules_overlay = overlay
            fl.add_widget(dim)
            fl.add_widget(overlay)

        def _rules_close_overlay(self):
            """Lukk regelinnhold-overlay."""
            if self._rules_overlay and self._rules_overlay.parent:
                fl = self._rules_overlay.parent
                fl.remove_widget(self._rules_overlay)
                if hasattr(self, '_rules_dim') and self._rules_dim and self._rules_dim.parent:
                    fl.remove_widget(self._rules_dim)
            self._rules_overlay = None
            self._rules_dim = None


        # ---------- CAST ----------
        def _mk_cast(self):
            p = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
            if not CAST_AVAILABLE:
                p.add_widget(mklbl("Casting utilgjengelig\npychromecast mangler", color=DIM, size=13))
                return p
            self.cast_lbl = mklbl("Ikke tilkoblet", color=DIM, size=13, h=30)
            p.add_widget(self.cast_lbl)
            p.add_widget(mkbtn("Sok etter enheter", self._scan, accent=True,
                               size_hint_y=None, height=dp(46)))
            self.cast_sp = Spinner(text="Velg enhet...", values=[],
                                   size_hint_y=None, height=dp(46),
                                   background_color=BTN, color=TXT)
            p.add_widget(self.cast_sp)
            r = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
            r.add_widget(mkbtn("Koble til", self._cn, accent=True))
            r.add_widget(mkbtn("Koble fra", self._dc, danger=True))
            p.add_widget(r)
            p.add_widget(Widget(size_hint_y=1))
            return p

        def _scan(self):
            self.cast_lbl.text = "Soker..."
            self.cast.scan(cb=self._od)

        def _od(self, n):
            if n:
                self.cast_sp.values = n
                self.cast_sp.text = n[0]
            self.cast_lbl.text = f"Fant {len(n)}" if n else "Ingen"

        def _cn(self):
            n = self.cast_sp.text
            if not n or n == "Velg enhet...":
                return
            self.cast.connect(n, cb=lambda ok: setattr(
                self.cast_lbl, 'text', "Tilkoblet!" if ok else "Feilet"))

        def _dc(self):
            self.cast.disconnect()
            self.cast_lbl.text = "Frakoblet"

        # ---------- KARAKTERER ----------
        def _mk_tool(self):
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            tb = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6), padding=[dp(6), 0])
            tb.add_widget(mkbtn("+ Ny", self._new_char, accent=True, size_hint_x=0.35))
            tb.add_widget(mkbtn("Oppdater", self._show_list, small=True, size_hint_x=0.35))
            tb.add_widget(mklbl("Karakterer", color=GOLD, size=14, bold=True))
            p.add_widget(tb)
            self.tool_area = BoxLayout()
            p.add_widget(self.tool_area)
            self._show_list()
            return p

        # ---------- D&D 5E KARAKTERER ----------
        @staticmethod
        def _mod(score):
            """Beregn ability modifier: (score - 10) // 2."""
            try:
                s = int(score)
            except (ValueError, TypeError):
                s = 10
            return (s - 10) // 2

        @staticmethod
        def _fmt_mod(score_str):
            """Formater modifier som +N / -N for visning."""
            try:
                s = int(score_str or '10')
            except (ValueError, TypeError):
                s = 10
            return f"{(s - 10) // 2:+d}"

        def _show_list(self):
            self.tool_area.clear_widgets()
            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(6), padding=dp(6), size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))
            if not self.chars:
                g.add_widget(mklbl("Ingen karakterer ennaa.\nTrykk '+ Ny' for aa lage en.",
                                   color=DIM, size=12, h=50))
            else:
                for i, ch in enumerate(self.chars):
                    nm = ch.get('name', '?')
                    tp = ch.get('type', 'PC')
                    lvl = ch.get('level', '')
                    cls = ch.get('class', '')
                    spc = ch.get('species', '')
                    c = GRN if tp == 'PC' else GOLD
                    sub = " / ".join(s for s in [
                        f"Lv {lvl}" if lvl else "",
                        spc, cls
                    ] if s)
                    txt = f"[{tp}]  {nm}" + (f"  -  {sub}" if sub else "")
                    row = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(6))
                    b = mkbtn(txt, lambda idx=i: self._view_char(idx),
                              small=True, size_hint_x=0.72)
                    b.color = c
                    b.halign = 'left'
                    row.add_widget(b)
                    row.add_widget(mkbtn("Rediger", lambda idx=i: self._edit_char(idx),
                                         accent=True, small=True, size_hint_x=0.28))
                    g.add_widget(row)
            scroll.add_widget(g)
            self.tool_area.add_widget(scroll)

        def _view_char(self, idx):
            if idx < 0 or idx >= len(self.chars):
                return
            ch = self.chars[idx]
            self.tool_area.clear_widgets()
            p = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(6))
            top = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            top.add_widget(mkbtn("Tilbake", self._show_list, small=True, size_hint_x=0.3))
            top.add_widget(mkbtn("Rediger", lambda: self._edit_char(idx),
                                 accent=True, small=True, size_hint_x=0.3))
            top.add_widget(mkbtn("Slett", lambda: self._del_char(idx),
                                 danger=True, small=True, size_hint_x=0.3))
            p.add_widget(top)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(6), size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            nm = ch.get('name', '?')
            tp = ch.get('type', 'PC')
            g.add_widget(mklbl(f"[{tp}]  {nm}", color=GOLD, size=18, bold=True, h=34))

            # Grunninfo-linje
            info_parts = []
            lvl = ch.get('level', '')
            if lvl:
                info_parts.append(f"Level {lvl}")
            for k in ['species', 'class', 'subclass', 'background']:
                v = ch.get(k, '')
                if v:
                    info_parts.append(str(v))
            if info_parts:
                g.add_widget(mklbl(" | ".join(info_parts), color=TXT, size=13, h=22))
            align = ch.get('alignment', '')
            if align:
                g.add_widget(mklbl(f"Alignment: {align}", color=DIM, size=12, h=20))

            # --- Kamp: AC / HP / Init / Speed / PB ---
            g.add_widget(mksep(4))
            g.add_widget(mklbl("KAMP", color=GOLD, size=13, bold=True, h=24))
            ab_data = ch.get('abilities', {})
            dex_mod = self._mod(ab_data.get('DEX', {}).get('score', 10))
            pb = ch.get('proficiency_bonus', 2)
            combat_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(4))
            for lbl, v in [
                ("AC", ch.get('armor_class', 10)),
                ("HP", f"{ch.get('hp_current', 0)}/{ch.get('hp_max', 0)}"),
                ("Init", f"{dex_mod:+d}"),
                ("Speed", ch.get('speed', 30)),
                ("PB", f"+{pb}"),
            ]:
                fb = FramedBox(orientation='vertical', size_hint_x=1,
                               padding=dp(4), spacing=dp(2))
                fb.add_widget(Label(text=lbl, font_size=sp(10), color=GOLD, bold=True))
                fb.add_widget(Label(text=str(v), font_size=sp(13), color=TXT, bold=True))
                combat_row.add_widget(fb)
            g.add_widget(combat_row)

            if ch.get('hp_temp'):
                g.add_widget(mklbl(f"Temp HP: {ch['hp_temp']}", color=TXT, size=11, h=18))
            hd = ch.get('hit_dice_max', '')
            if hd:
                spent = ch.get('hit_dice_spent', 0)
                g.add_widget(mklbl(f"Hit Dice: {hd} (brukt: {spent})",
                                   color=TXT, size=11, h=18))
            ds = ch.get('death_successes', 0)
            df = ch.get('death_failures', 0)
            if ds or df:
                g.add_widget(mklbl(f"Death saves:  ✓ {ds}   ✗ {df}",
                                   color=TXT, size=11, h=18))
            if ch.get('heroic_inspiration'):
                g.add_widget(mklbl("⬥ Heroic Inspiration", color=GOLD, size=11, h=18))

            # --- Ability Scores med save-info ---
            g.add_widget(mksep(4))
            g.add_widget(mklbl("ABILITY SCORES", color=GOLD, size=13, bold=True, h=24))
            ab_row = BoxLayout(size_hint_y=None, height=dp(60), spacing=dp(4))
            for ab in DND_ABILITIES:
                a = ab_data.get(ab, {})
                score = a.get('score', 10)
                mod = self._mod(score)
                save_bonus = mod + (pb if a.get('save_prof') else 0)
                fb = FramedBox(orientation='vertical', size_hint_x=1,
                               padding=dp(3), spacing=dp(1))
                fb.add_widget(Label(text=ab, font_size=sp(10), color=GOLD, bold=True))
                fb.add_widget(Label(text=str(score), font_size=sp(13),
                                    color=TXT, bold=True))
                fb.add_widget(Label(text=f"{mod:+d}", font_size=sp(10), color=TXT))
                fb.add_widget(Label(text=f"Sv {save_bonus:+d}",
                                    font_size=sp(9),
                                    color=GOLD if a.get('save_prof') else GDIM))
                ab_row.add_widget(fb)
            g.add_widget(ab_row)

            # --- Skills (kun proficient/expertise) ---
            sk_data = ch.get('skills', {})
            prof_skills = [(n, a) for n, a in DND_SKILLS
                           if sk_data.get(n, {}).get('prof')
                           or sk_data.get(n, {}).get('expertise')]
            if prof_skills:
                g.add_widget(mksep(4))
                g.add_widget(mklbl("SKILLS (proficient)", color=GOLD,
                                   size=13, bold=True, h=24))
                for sname, sab in prof_skills:
                    sd = sk_data[sname]
                    mod = self._mod(ab_data.get(sab, {}).get('score', 10))
                    bonus = mod + pb * (2 if sd.get('expertise') else 1)
                    tag = " ★" if sd.get('expertise') else ""
                    framed = FramedBox(orientation='horizontal', size_hint_y=None,
                                       height=dp(30), padding=dp(4), spacing=dp(4))
                    framed.add_widget(mklbl(f"{sname} ({sab}){tag}:  {bonus:+d}",
                                            color=TXT, size=12, wrap=True))
                    g.add_widget(framed)

            # --- Armor training ---
            at = ch.get('armor_training', {})
            trained = [k.capitalize() for k in ['light', 'medium', 'heavy', 'shields']
                       if at.get(k)]
            if trained:
                g.add_widget(mksep(4))
                g.add_widget(mklbl("ARMOR TRAINING", color=GOLD, size=13, bold=True, h=24))
                g.add_widget(mklbl(", ".join(trained), color=TXT, size=12, h=22))

            # --- Weapon prof / Tools / Languages ---
            for k, lbl in [('weapon_prof', 'Vaapentrening'),
                           ('tool_prof',   'Verktoey'),
                           ('languages',   'Spraak')]:
                v = ch.get(k, '')
                if v:
                    g.add_widget(mklbl(f"{lbl}: {v}", color=TXT, size=12, h=22, wrap=True))

            # --- Tekstblokker ---
            for k, lbl in [('weapons',         'VAAPEN'),
                           ('class_features',  'KLASSE-EGENSKAPER'),
                           ('species_traits',  'SPECIES-TREKK'),
                           ('feats',           'FEATS')]:
                v = ch.get(k, '')
                if v:
                    g.add_widget(mksep(4))
                    g.add_widget(mklbl(lbl, color=GOLD, size=13, bold=True, h=24))
                    g.add_widget(mklbl(str(v), color=TXT, size=12, wrap=True))

            # --- Spellcasting ---
            sa = ch.get('spell_ability', '')
            slots = ch.get('spell_slots', {})
            any_slots = any((slots.get(str(l), {}).get('total', 0) > 0)
                            for l in range(1, 10))
            if sa or any_slots or ch.get('spells'):
                g.add_widget(mksep(4))
                g.add_widget(mklbl("SPELLCASTING", color=GOLD, size=13, bold=True, h=24))
                if sa:
                    dc = ch.get('spell_save_dc', 0)
                    ab = ch.get('spell_attack_bonus', 0)
                    g.add_widget(mklbl(
                        f"Ability: {sa}  |  Save DC: {dc}  |  Atk: {ab:+d}",
                        color=TXT, size=12, h=22))
                slot_parts = []
                for lvl in range(1, 10):
                    s = slots.get(str(lvl), {})
                    t = s.get('total', 0)
                    if t > 0:
                        e = s.get('expended', 0)
                        slot_parts.append(f"L{lvl}: {t - e}/{t}")
                if slot_parts:
                    g.add_widget(mklbl("  ".join(slot_parts),
                                       color=TXT, size=11, h=20, wrap=True))
                sp_list = ch.get('spells', '')
                if sp_list:
                    g.add_widget(mklbl(str(sp_list), color=TXT, size=11, wrap=True))

            # --- Beskrivelse ---
            for k, lbl in [('appearance', 'UTSEENDE'),
                           ('backstory',  'BAKGRUNN'),
                           ('equipment',  'UTSTYR')]:
                v = ch.get(k, '')
                if v:
                    g.add_widget(mksep(4))
                    g.add_widget(mklbl(lbl, color=GOLD, size=13, bold=True, h=24))
                    g.add_widget(mklbl(str(v), color=TXT, size=12, wrap=True))

            # --- Attunement ---
            att = ch.get('attunement', [])
            att_used = [a for a in att if a]
            if att_used:
                g.add_widget(mksep(4))
                g.add_widget(mklbl("ATTUNEMENT", color=GOLD, size=13, bold=True, h=24))
                for a in att_used:
                    g.add_widget(mklbl(f"• {a}", color=TXT, size=12, h=22, wrap=True))

            # --- Mynter ---
            coins = ch.get('coins', {})
            if any(coins.get(c, 0) for c in ['cp', 'sp', 'ep', 'gp', 'pp']):
                g.add_widget(mksep(4))
                g.add_widget(mklbl("MYNTER", color=GOLD, size=13, bold=True, h=24))
                coin_parts = [f"{coins.get(c, 0)} {c.upper()}"
                              for c in ['cp', 'sp', 'ep', 'gp', 'pp']
                              if coins.get(c, 0)]
                g.add_widget(mklbl("   ".join(coin_parts), color=TXT, size=12, h=22))

            scroll.add_widget(g)
            p.add_widget(scroll)
            self.tool_area.add_widget(p)

        def _new_char(self):
            """Opprett ny D&D 5e 2024-karakter med standardverdier."""
            new_char = {
                'type': 'PC',
                'name': 'Ny karakter',
                'species': '', 'class': '', 'subclass': '',
                'background': '', 'alignment': '',
                'level': 1, 'xp': 0, 'proficiency_bonus': 2,
                'armor_class': 10, 'initiative': 0, 'speed': 30,
                'size': 'Medium', 'passive_perception': 10,
                'hp_current': 0, 'hp_max': 0, 'hp_temp': 0,
                'hit_dice_max': '1d8', 'hit_dice_spent': 0,
                'death_successes': 0, 'death_failures': 0,
                'heroic_inspiration': False,
                'abilities': {ab: {'score': 10, 'save_prof': False}
                              for ab in DND_ABILITIES},
                'skills': {n: {'prof': False, 'expertise': False}
                           for n, _ in DND_SKILLS},
                'armor_training': {'light': False, 'medium': False,
                                   'heavy': False, 'shields': False},
                'weapon_prof': '', 'tool_prof': '', 'languages': '',
                'weapons': '',
                'class_features': '', 'species_traits': '', 'feats': '',
                'spell_ability': '', 'spell_save_dc': 0, 'spell_attack_bonus': 0,
                'spell_slots': {str(l): {'total': 0, 'expended': 0}
                                for l in range(1, 10)},
                'spells': '',
                'appearance': '', 'backstory': '', 'equipment': '',
                'attunement': ['', '', ''],
                'coins': {'cp': 0, 'sp': 0, 'ep': 0, 'gp': 0, 'pp': 0},
            }
            self.chars.append(new_char)
            save_json(CHAR_FILE, self.chars)
            self._edit_char(len(self.chars) - 1)

        def _edit_char(self, idx):
            if idx < 0 or idx >= len(self.chars):
                return
            self.edit_idx = idx
            ch = self.chars[idx]
            self.tool_area.clear_widgets()
            p = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(6))
            top = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            top.add_widget(mkbtn("Lagre",  self._save_edit, accent=True,
                                 small=True, size_hint_x=0.5))
            top.add_widget(mkbtn("Avbryt", self._show_list, small=True, size_hint_x=0.5))
            p.add_widget(top)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(6), size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))
            self._ei = {}

            # --- Lokale builders ---
            def ti(key, value='', int_only=False, multiline=False, height=36, sx=1):
                txt = '' if value == '' or value is None else str(value)
                w = TextInput(text=txt, font_size=sp(12), multiline=multiline,
                              background_color=BTN, foreground_color=TXT,
                              size_hint_x=sx, padding=[dp(6), dp(4)])
                if int_only:
                    w.input_filter = 'int'
                if multiline:
                    w.size_hint_y = None
                    w.height = dp(height)
                self._ei[key] = w
                return w

            def ml(text, sx=None, halign='right', size=10, color=DIM):
                lb = Label(text=text, font_size=sp(size), color=color,
                           halign=halign, valign='middle')
                if sx is not None:
                    lb.size_hint_x = sx
                lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                return lb

            def row_h(h=36, spacing=6):
                return BoxLayout(size_hint_y=None, height=dp(h), spacing=dp(spacing))

            def toggle(key, state):
                t = RToggle(text='v', state='down' if state else 'normal',
                            color=GOLD, bg_color=BTN, font_size=sp(11))
                self._ei[key] = t
                return t

            # --- 1. GRUNNINFO ---
            g.add_widget(mklbl("GRUNNINFO", color=GOLD, size=12, bold=True, h=24))
            r = row_h()
            r.add_widget(ml("Navn", sx=0.18))
            r.add_widget(ti('name', ch.get('name', ''), sx=0.52))
            r.add_widget(ml("Type", sx=0.12))
            tp_sp = Spinner(text=ch.get('type', 'PC'), values=['PC', 'NPC'],
                            background_color=BTN, color=GOLD,
                            font_size=sp(11), size_hint_x=0.18)
            self._ei['type'] = tp_sp
            r.add_widget(tp_sp)
            g.add_widget(r)

            for a_key, a_lbl, b_key, b_lbl in [
                ('species',  'Species',   'class',      'Klasse'),
                ('subclass', 'Subklasse', 'background', 'Bakgrunn'),
            ]:
                r = row_h()
                r.add_widget(ml(a_lbl, sx=0.18))
                r.add_widget(ti(a_key, ch.get(a_key, ''), sx=0.32))
                r.add_widget(ml(b_lbl, sx=0.18))
                r.add_widget(ti(b_key, ch.get(b_key, ''), sx=0.32))
                g.add_widget(r)

            r = row_h()
            r.add_widget(ml("Level", sx=0.15))
            r.add_widget(ti('level', ch.get('level', 1), int_only=True, sx=0.15))
            r.add_widget(ml("XP", sx=0.1))
            r.add_widget(ti('xp', ch.get('xp', 0), int_only=True, sx=0.25))
            r.add_widget(ml("PB", sx=0.1))
            r.add_widget(ti('proficiency_bonus', ch.get('proficiency_bonus', 2),
                            int_only=True, sx=0.15))
            g.add_widget(r)

            r = row_h()
            r.add_widget(ml("Alignment", sx=0.25))
            r.add_widget(ti('alignment', ch.get('alignment', ''), sx=0.75))
            g.add_widget(r)

            # --- 2. KAMP ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("KAMP & BEVEGELSE", color=GOLD,
                               size=12, bold=True, h=24))
            r = row_h()
            r.add_widget(ml("AC", sx=0.08))
            r.add_widget(ti('armor_class', ch.get('armor_class', 10),
                            int_only=True, sx=0.15))
            r.add_widget(ml("Init", sx=0.1))
            r.add_widget(ti('initiative', ch.get('initiative', 0),
                            int_only=True, sx=0.15))
            r.add_widget(ml("Speed", sx=0.13))
            r.add_widget(ti('speed', ch.get('speed', 30),
                            int_only=True, sx=0.13))
            r.add_widget(ml("PassP", sx=0.13))
            r.add_widget(ti('passive_perception', ch.get('passive_perception', 10),
                            int_only=True, sx=0.13))
            g.add_widget(r)

            r = row_h()
            r.add_widget(ml("Size", sx=0.15))
            r.add_widget(ti('size', ch.get('size', 'Medium'), sx=0.4))
            r.add_widget(ml("Heroic Insp", sx=0.3))
            t = toggle('heroic_inspiration', ch.get('heroic_inspiration', False))
            t.size_hint_x = 0.15
            r.add_widget(t)
            g.add_widget(r)

            # --- 3. HIT POINTS / DEATH SAVES ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("HIT POINTS & DEATH SAVES", color=GOLD,
                               size=12, bold=True, h=24))
            r = row_h()
            r.add_widget(ml("HP", sx=0.1))
            r.add_widget(ti('hp_current', ch.get('hp_current', 0),
                            int_only=True, sx=0.18))
            r.add_widget(ml("Max", sx=0.1))
            r.add_widget(ti('hp_max', ch.get('hp_max', 0),
                            int_only=True, sx=0.18))
            r.add_widget(ml("Temp", sx=0.12))
            r.add_widget(ti('hp_temp', ch.get('hp_temp', 0),
                            int_only=True, sx=0.18))
            g.add_widget(r)

            r = row_h()
            r.add_widget(ml("Hit Dice", sx=0.22))
            r.add_widget(ti('hit_dice_max', ch.get('hit_dice_max', '1d8'), sx=0.28))
            r.add_widget(ml("Brukt", sx=0.18))
            r.add_widget(ti('hit_dice_spent', ch.get('hit_dice_spent', 0),
                            int_only=True, sx=0.2))
            g.add_widget(r)

            r = row_h()
            r.add_widget(ml("Death v", sx=0.22))
            r.add_widget(ti('death_successes', ch.get('death_successes', 0),
                            int_only=True, sx=0.18))
            r.add_widget(ml("Death x", sx=0.22))
            r.add_widget(ti('death_failures', ch.get('death_failures', 0),
                            int_only=True, sx=0.18))
            g.add_widget(r)

            # --- 4. ABILITY SCORES med live mod-visning ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("ABILITY SCORES", color=GOLD,
                               size=12, bold=True, h=24))
            g.add_widget(mklbl("Evne    Score   Mod    Save prof",
                               color=GDIM, size=10, h=20))

            ab_data = ch.get('abilities', {})
            for ab in DND_ABILITIES:
                ad = ab_data.get(ab, {'score': 10, 'save_prof': False})
                r = row_h()
                r.add_widget(ml(ab, sx=0.18, halign='left', size=12, color=GOLD))
                sc_in = ti(f'ab_{ab}_score', ad.get('score', 10),
                           int_only=True, sx=0.2)
                r.add_widget(sc_in)
                mod_lb = Label(text=self._fmt_mod(ad.get('score', 10)),
                               font_size=sp(13), color=TXT, bold=True,
                               size_hint_x=0.18)
                # Live update mod-label naar score endres
                sc_in.bind(text=lambda inst, v, m=mod_lb:
                           setattr(m, 'text', self._fmt_mod(v)))
                r.add_widget(mod_lb)
                r.add_widget(ml("Save", sx=0.25))
                t = toggle(f'ab_{ab}_save', ad.get('save_prof', False))
                t.size_hint_x = 0.19
                r.add_widget(t)
                g.add_widget(r)

            # --- 5. SKILLS (Prof / Expertise toggles + live bonus) ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("SKILLS", color=GOLD, size=12, bold=True, h=24))
            g.add_widget(mklbl("Bonus = Mod + PB (prof) + PB (expertise)",
                               color=GDIM, size=9, h=18))
            g.add_widget(mklbl("Ferdighet           Prof  Exp  Bonus",
                               color=GDIM, size=10, h=20))
            sk_data = ch.get('skills', {})
            for sname, sab in DND_SKILLS:
                sd = sk_data.get(sname, {'prof': False, 'expertise': False})
                r = row_h(h=32, spacing=4)
                r.add_widget(ml(f"{sname} ({sab})", sx=0.5,
                                halign='left', size=11, color=TXT))
                t1 = toggle(f'sk_{sname}_prof', sd.get('prof', False))
                t1.size_hint_x = 0.15
                r.add_widget(t1)
                t2 = toggle(f'sk_{sname}_exp', sd.get('expertise', False))
                t2.size_hint_x = 0.15
                r.add_widget(t2)
                bonus_lb = Label(text='', font_size=sp(12), color=GOLD,
                                 bold=True, size_hint_x=0.2,
                                 halign='center', valign='middle')
                bonus_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                r.add_widget(bonus_lb)

                # Closure som beregner bonus live
                def _upd(*_a, ab=sab, lb=bonus_lb, pt=t1, et=t2):
                    try:
                        score_w = self._ei.get(f'ab_{ab}_score')
                        score = int(score_w.text) if (score_w and score_w.text) else 10
                    except (ValueError, AttributeError):
                        score = 10
                    try:
                        pb_w = self._ei.get('proficiency_bonus')
                        pb = int(pb_w.text) if (pb_w and pb_w.text) else 2
                    except (ValueError, AttributeError):
                        pb = 2
                    mod = (score - 10) // 2
                    bonus = mod
                    if pt.state == 'down':
                        bonus += pb
                        if et.state == 'down':
                            bonus += pb
                    lb.text = f'{bonus:+d}'

                _upd()  # initial visning
                # Re-beregn naar noe relevant endres
                sc_w = self._ei.get(f'ab_{sab}_score')
                if sc_w:
                    sc_w.bind(text=_upd)
                pb_w = self._ei.get('proficiency_bonus')
                if pb_w:
                    pb_w.bind(text=_upd)
                t1.bind(state=_upd)
                t2.bind(state=_upd)

                g.add_widget(r)

            # --- 6. TRENING & SPRAAK ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("TRENING & SPRAAK", color=GOLD,
                               size=12, bold=True, h=24))
            at = ch.get('armor_training', {})
            r = row_h()
            r.add_widget(ml("Armor", sx=0.18, halign='left'))
            for a in ['light', 'medium', 'heavy', 'shields']:
                r.add_widget(ml(a[:4].capitalize(), sx=0.1, size=9))
                t = toggle(f'armor_{a}', at.get(a, False))
                t.size_hint_x = 0.105
                r.add_widget(t)
            g.add_widget(r)

            for k, lbl in [('weapon_prof', 'Vaapen-trening'),
                           ('tool_prof',   'Verktoey-trening'),
                           ('languages',   'Spraak')]:
                g.add_widget(mklbl(lbl, color=DIM, size=10, h=20))
                g.add_widget(ti(k, ch.get(k, ''), multiline=True, height=52))

            # --- 7. VAAPEN ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("VAAPEN", color=GOLD, size=12, bold=True, h=24))
            g.add_widget(mklbl("Format: Navn | Atk/DC | Skade | Notater",
                               color=GDIM, size=9, h=18))
            g.add_widget(ti('weapons', ch.get('weapons', ''),
                            multiline=True, height=100))

            # --- 8. EGENSKAPER ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("EGENSKAPER", color=GOLD, size=12, bold=True, h=24))
            for k, lbl in [('class_features',  'Klasse-egenskaper'),
                           ('species_traits',  'Species-trekk'),
                           ('feats',           'Feats')]:
                g.add_widget(mklbl(lbl, color=DIM, size=10, h=20))
                g.add_widget(ti(k, ch.get(k, ''), multiline=True, height=80))

            # --- 9. SPELLCASTING ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("SPELLCASTING", color=GOLD, size=12, bold=True, h=24))
            r = row_h()
            r.add_widget(ml("Ability", sx=0.2))
            sa_val = ch.get('spell_ability', '') or '-'
            sa_sp = Spinner(text=sa_val, values=['-', 'INT', 'WIS', 'CHA'],
                            background_color=BTN, color=GOLD,
                            font_size=sp(11), size_hint_x=0.2)
            self._ei['spell_ability'] = sa_sp
            r.add_widget(sa_sp)
            r.add_widget(ml("Save DC", sx=0.18))
            r.add_widget(ti('spell_save_dc', ch.get('spell_save_dc', 0),
                            int_only=True, sx=0.12))
            r.add_widget(ml("Atk", sx=0.15))
            r.add_widget(ti('spell_attack_bonus', ch.get('spell_attack_bonus', 0),
                            int_only=True, sx=0.15))
            g.add_widget(r)

            g.add_widget(mklbl("Spell slots  (total / brukt)",
                               color=DIM, size=10, h=20))
            slots = ch.get('spell_slots', {})
            for lvl in range(1, 10):
                s = slots.get(str(lvl), {'total': 0, 'expended': 0})
                r = row_h(h=32)
                r.add_widget(ml(f"L{lvl}", sx=0.18, halign='left',
                                color=GOLD, size=11))
                r.add_widget(ml("Total", sx=0.18))
                r.add_widget(ti(f'slot_{lvl}_total', s.get('total', 0),
                                int_only=True, sx=0.18))
                r.add_widget(ml("Brukt", sx=0.18))
                r.add_widget(ti(f'slot_{lvl}_expended', s.get('expended', 0),
                                int_only=True, sx=0.18))
                g.add_widget(r)

            g.add_widget(mklbl("Cantrips & Prepared Spells",
                               color=DIM, size=10, h=20))
            g.add_widget(ti('spells', ch.get('spells', ''),
                            multiline=True, height=120))

            # --- 10. BESKRIVELSE ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("BESKRIVELSE", color=GOLD,
                               size=12, bold=True, h=24))
            for k, lbl in [('appearance', 'Utseende'),
                           ('backstory',  'Bakgrunn'),
                           ('equipment',  'Utstyr')]:
                g.add_widget(mklbl(lbl, color=DIM, size=10, h=20))
                g.add_widget(ti(k, ch.get(k, ''), multiline=True, height=80))

            # --- 11. ATTUNEMENT (3 slots) ---
            g.add_widget(mklbl("Magic Item Attunement (maks 3)",
                               color=DIM, size=10, h=20))
            att = list(ch.get('attunement', ['', '', '']))
            while len(att) < 3:
                att.append('')
            for i in range(3):
                r = row_h()
                r.add_widget(ml(f"Slot {i+1}", sx=0.22))
                r.add_widget(ti(f'attune_{i}', att[i], sx=0.78))
                g.add_widget(r)

            # --- 12. MYNTER ---
            g.add_widget(mksep(6))
            g.add_widget(mklbl("MYNTER", color=GOLD, size=12, bold=True, h=24))
            coins = ch.get('coins', {})
            r = row_h()
            for c in ['cp', 'sp', 'ep', 'gp', 'pp']:
                r.add_widget(ml(c.upper(), sx=0.08, halign='center', size=11))
                r.add_widget(ti(f'coin_{c}', coins.get(c, 0),
                                int_only=True, sx=0.12))
            g.add_widget(r)

            scroll.add_widget(g)
            p.add_widget(scroll)
            self.tool_area.add_widget(p)

        def _save_edit(self):
            if self.edit_idx is None or self.edit_idx >= len(self.chars):
                return
            ch = self.chars[self.edit_idx]

            def get_text(k, default=''):
                w = self._ei.get(k)
                if w is None:
                    return default
                return w.text.strip() if hasattr(w, 'text') else default

            def get_int(k, default=0):
                t = get_text(k, '')
                try:
                    return int(t) if t else default
                except ValueError:
                    return default

            def get_bool(k):
                w = self._ei.get(k)
                return bool(w and getattr(w, 'state', 'normal') == 'down')

            # Enkle strenger
            for k in ['name', 'type', 'species', 'class', 'subclass', 'background',
                     'alignment', 'size', 'hit_dice_max', 'spell_ability',
                     'weapon_prof', 'tool_prof', 'languages',
                     'weapons', 'class_features', 'species_traits', 'feats',
                     'appearance', 'backstory', 'equipment', 'spells']:
                ch[k] = get_text(k)

            # '-' i Spinner betyr "ingen"
            if ch.get('spell_ability') == '-':
                ch['spell_ability'] = ''

            # Heltall
            for k in ['level', 'xp', 'proficiency_bonus', 'armor_class',
                     'initiative', 'speed', 'passive_perception',
                     'hp_current', 'hp_max', 'hp_temp', 'hit_dice_spent',
                     'death_successes', 'death_failures',
                     'spell_save_dc', 'spell_attack_bonus']:
                ch[k] = get_int(k)

            # Toggles
            ch['heroic_inspiration'] = get_bool('heroic_inspiration')

            # Abilities
            ch['abilities'] = {
                ab: {
                    'score':     get_int(f'ab_{ab}_score', 10),
                    'save_prof': get_bool(f'ab_{ab}_save'),
                }
                for ab in DND_ABILITIES
            }

            # Skills
            ch['skills'] = {
                sname: {
                    'prof':      get_bool(f'sk_{sname}_prof'),
                    'expertise': get_bool(f'sk_{sname}_exp'),
                }
                for sname, _ in DND_SKILLS
            }

            # Armor training
            ch['armor_training'] = {
                a: get_bool(f'armor_{a}')
                for a in ['light', 'medium', 'heavy', 'shields']
            }

            # Spell slots
            ch['spell_slots'] = {
                str(lvl): {
                    'total':    get_int(f'slot_{lvl}_total'),
                    'expended': get_int(f'slot_{lvl}_expended'),
                }
                for lvl in range(1, 10)
            }

            # Attunement
            ch['attunement'] = [get_text(f'attune_{i}') for i in range(3)]

            # Mynter
            ch['coins'] = {c: get_int(f'coin_{c}')
                           for c in ['cp', 'sp', 'ep', 'gp', 'pp']}

            save_json(CHAR_FILE, self.chars)
            self._show_list()

        def _del_char(self, idx):
            if 0 <= idx < len(self.chars):
                self.chars.pop(idx)
                save_json(CHAR_FILE, self.chars)
                self._show_list()

        def on_stop(self):
            self.player.stop()
            self.streamer.stop()
            self.server.stop()
            self.cast.disconnect()
            save_json(CHAR_FILE, self.chars)

    log("Starting app...")
    CampaignForgeApp().run()

except Exception as e:
    log(f"CRASH: {e}")
    log(traceback.format_exc())
