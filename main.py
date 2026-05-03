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

    # PIL for battlemap compositing
    try:
        from PIL import Image as PILImage, ImageDraw as PILDraw, ImageFont as PILFont
        PIL_OK = True
        log("PIL imported OK")
    except ImportError:
        PIL_OK = False
        log("PIL NOT available - battlemap disabled")

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
    ONESHOT_DIR = os.path.join(BASE_DIR, "oneshots")
    MAPS_DIR  = os.path.join(BASE_DIR, "maps")
    CHAR_FILE = os.path.join(BASE_DIR, "characters.json")
    SCENARIO_FILE = os.path.join(BASE_DIR, "scenarios.json")
    BATTLE_FILE = os.path.join(BASE_DIR, "battlemap.json")
    BATTLE_PNG  = os.path.join(BASE_DIR, "battlemap_current.png")
    # Canvas resolution for battlemap (16:9, suits TV casting)
    CANVAS_W = 1280
    CANVAS_H = 720
    FT_PER_SQUARE = 5   # D&D 5e standard

    def ensure_dirs():
        """Opprett mapper ETTER tillatelser er gitt."""
        for d in [IMG_DIR, MUSIC_DIR, ONESHOT_DIR, MAPS_DIR]:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                log(f"makedirs {d}: {e}")
        log(f"Dirs OK: img={os.path.exists(IMG_DIR)}, mus={os.path.exists(MUSIC_DIR)}, one={os.path.exists(ONESHOT_DIR)}")

    # === FARGER – EMERALD GROVE (lys D&D-tema med grønt) ===
    BG   = [0.16, 0.19, 0.15, 1]      # lys mosegrønn-brun bakgrunn
    BG2  = [0.23, 0.27, 0.22, 1]      # pergament-panel (lys olivengrønn)
    INPUT= [0.11, 0.14, 0.10, 1]      # tekstfelt-bakgrunn (lesbar kontrast)
    BTN  = [0.32, 0.42, 0.30, 1]      # skogsgrønn knapp
    BTNH = [0.48, 0.62, 0.38, 1]      # aktiv fane (lys vårgrønn)
    SHAD = [0.05, 0.07, 0.04, 0.4]    # skygge
    GOLD = [1.00, 0.85, 0.45, 1]      # varmt gull (D&D-aksent)
    GDIM = [0.75, 0.65, 0.38, 1]      # dempet gull
    TXT  = [0.97, 0.95, 0.85, 1]      # lys pergament-tekst
    DIM  = [0.78, 0.78, 0.65, 1]      # lys dempet tekst
    RED  = [0.85, 0.35, 0.25, 1]      # dragen-rød (fare/stopp)
    GRN  = [0.55, 0.78, 0.42, 1]      # lys vårgrønn (OK/PC)
    BLUE = [0.42, 0.58, 0.78, 1]      # stålblå (info)
    BLK  = [0.0, 0.0, 0.0, 1]         # svart (preview-bg)
    # === SCENARIO-BOKSER ===
    LOOP_BG    = [0.32, 0.42, 0.30, 1] # som BTN – loop-bokser
    LOOP_BG_ON = [0.42, 0.58, 0.34, 1] # lysere når lagspilles
    ONE_BG     = [0.18, 0.13, 0.10, 1] # mørk brun – oneshot-bokser
    ONE_BORDER = [1.00, 0.85, 0.45, 1] # gull-ramme på oneshot-bokser
    IMG_EXT   = ('.png','.jpg','.jpeg','.webp')
    SND_EXT   = ('.mp3','.ogg','.wav','.flac','.m4a','.aac')
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

    class _BMImage(Image):
        """Image-widget for battlemap: konverterer trykk til canvas-px.

        touch_cb kalles med (canvas_x, canvas_y) i CANVAS_W x CANVAS_H omraade.
        Appen selv konverterer til grid-ruter.
        """
        def __init__(self, touch_cb=None, **kw):
            super().__init__(**kw)
            self._touch_cb = touch_cb

        def on_touch_down(self, touch):
            if not self.collide_point(*touch.pos):
                return False
            if not self._touch_cb:
                return False
            nw, nh = self.norm_image_size
            if nw <= 0 or nh <= 0:
                return False
            # Bildet er sentrert i widgeten (keep_ratio=True)
            off_x = self.x + (self.width - nw) / 2.0
            off_y = self.y + (self.height - nh) / 2.0
            ix = touch.x - off_x
            iy = touch.y - off_y
            if ix < 0 or iy < 0 or ix > nw or iy > nh:
                return False
            # Skaler til CANVAS-koord, flip y (Kivy origo nede, PIL oppe)
            cx = ix * CANVAS_W / nw
            cy = (nh - iy) * CANVAS_H / nh
            self._touch_cb(cx, cy)
            return True

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
        {"name":"--- Kro og by ---"},
        {"name":"Middelaldersk by","url":"https://archive.org/download/056_medieval_town/056_medieval_town.mp3"},
        {"name":"Kro 1","url":"https://archive.org/download/Tavern3/Tavern%201.mp3"},
        {"name":"Kro 2","url":"https://archive.org/download/Tavern3/Tavern%202.mp3"},
        {"name":"Kro 3","url":"https://archive.org/download/Tavern3/Tavern%203.mp3"},
        {"name":"Kro 4","url":"https://archive.org/download/Tavern3/Tavern%204.mp3"},
        {"name":"Kro 5","url":"https://archive.org/download/Tavern3/Tavern%205.mp3"},
        {"name":"--- Dungeon og hule ---"},
        {"name":"Fuktig hule","url":"https://archive.org/download/watersoundsincave/Damp%20Cave.mp3"},
        {"name":"Mørk hule","url":"https://archive.org/download/watersoundsincave/Dark%20Cave.mp3"},
        {"name":"Dyp hule","url":"https://archive.org/download/watersoundsincave/Deep%20Cave%20Ambience.mp3"},
        {"name":"Ekkohule","url":"https://archive.org/download/watersoundsincave/Wave%20Echo%20Cave.mp3"},
        {"name":"Mørk atmosfære","url":"https://archive.org/download/watersoundsincave/Dark%20Ambience.mp3"},
        {"name":"Vann i hule","url":"https://archive.org/download/watersoundsincave/Water%20Sounds%20In%20Cave.mp3"},
        {"name":"--- Leir og bål ---"},
        {"name":"Leirbål ved elv","url":"https://archive.org/download/CampfireByTheRiverRelaxingFireplace/CampfireByTheRiverRelaxingFireplace.mp3"},
        {"name":"Leirbål ved sjø (natt)","url":"https://archive.org/download/CampfireByTheRiverRelaxingFireplace/CampfireByTheSeaCricketsOceanWavesNightForestRelaxing%20Fireplace.mp3"},
        {"name":"Koselig peis","url":"https://archive.org/download/CampfireByTheRiverRelaxingFireplace/LakesideCampfireWithRelaxing.mp3"},
        {"name":"Peis med storm","url":"https://archive.org/download/CampfireByTheRiverRelaxingFireplace/ThunderstormRainOnAWindowSoundThunderRainOnGlassAmbience.mp3"},
        {"name":"Regn på telt","url":"https://archive.org/download/CampfireByTheRiverRelaxingFireplace/NatureSoundsRainOnATent.mp3"},
        {"name":"--- Skog og villmark ---"},
        {"name":"Nattskog","url":"https://archive.org/download/NightSounds_201801/Soothing%20Night%20Time%20Forest%20Sounds.mp3"},
        {"name":"Myr om natten","url":"https://archive.org/download/NightSounds_201801/Swamp%20Sounds%20at%20Night%20-%20Frogs%2C%20Owls%2C%20Crickets%2C%20Light%20Rain%2C%20Forest%20Nature%20Sounds.mp3"},
        {"name":"Ugler og sirisser","url":"https://archive.org/download/NightSounds_201801/Owls%2C%20Crickets%2C%20Light%20Rain%2C%20Wind%20in%20Trees.mp3"},
        {"name":"Avslappende skog","url":"https://archive.org/download/NightSounds_201801/Relaxing%20Forest%20and%20Nature%20Soundscape.mp3"},
        {"name":"Skogbekk","url":"https://archive.org/download/CampfireByTheRiverRelaxingFireplace/ForestCreekSoundsSleepRelaxFocusMeditation.mp3"},
        {"name":"--- Kamp ---"},
        {"name":"Middelalderkamp","url":"https://archive.org/download/WarBattleSounds/Medieval%20battle%20sound%20effect%20-%20infantry.mp3"},
        {"name":"Slagmark","url":"https://archive.org/download/WarBattleSounds/War%20-%20Battle%20Sounds.mp3"},
        {"name":"--- Horror ---"},
        {"name":"Skummel atmosfære","url":"https://archive.org/download/creepy-music-sounds/Creepy%20music%20%26%20sounds.mp3"},
        {"name":"Uhyggelig drone","url":"https://archive.org/download/scary-sound-effects-8/Evil%20Demon%20Drone%20Movie%20Halloween%20Sounds.mp3"},
        {"name":"Mørk spenning","url":"https://archive.org/download/scary-sound-effects-8/Dramatic%20Suspense%20Sound%20Effects.mp3"},
        {"name":"Horrorlyder","url":"https://archive.org/download/creepy-music-sounds/Horror%20Sound%20Effects.mp3"},
    ]

    # === HERO'S JOURNEY (Vogler 12 steg) ===
    # Standardscener for nye scenarioer. Brukeren kan endre navn,
    # legge til nye eller fjerne underveis.
    VOGLER_STAGES = [
        "Den vanlige verden",
        "Eventyrets kall",
        "Avslag på kallet",
        "Møte med mentoren",
        "Krysse terskelen",
        "Prøvelser, allierte og fiender",
        "Nærmer seg den innerste hulen",
        "Ildprøven",
        "Belønningen",
        "Veien tilbake",
        "Gjenoppstandelsen",
        "Hjemkomst med eliksiren",
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
        ("Terningkast", [
          "d20 + modifikator vs DC.",
          "Lik eller over DC = suksess.",
          "",
          "Modifikator =",
          "  Ability mod + prof bonus",
          "  (hvis trent/proficient)",
          "",
          "Ability mod = (score - 10) / 2",
          "  Score 10-11: +0",
          "  Score 12-13: +1",
          "  Score 14-15: +2",
          "  Score 16-17: +3",
          "  Score 18-19: +4",
          "  Score 20:    +5",
          "",
          "Proficiency bonus:",
          "  Level 1-4:   +2",
          "  Level 5-8:   +3",
          "  Level 9-12:  +4",
          "  Level 13-16: +5",
          "  Level 17-20: +6",
        ]),
        ("Advantage & Disadvantage", [
          "Advantage: rull 2d20, bruk høyeste.",
          "Disadvantage: rull 2d20, bruk laveste.",
          "",
          "Flere adv/dis stacker IKKE.",
          "  1 adv + 1 dis = rull normalt.",
          "  2 adv + 1 dis = rull normalt.",
          "",
          "Gis av DM basert på situasjon:",
          "  Fordel: hjelp, godt lys, tid",
          "  Ulempe: dis syn, stress, utmattet",
          "",
          "Kan ikke kritisk ved dis,",
          "men kan kritisk ved adv.",
        ]),
        ("DC-referanse", [
          "DC 5:  Veldig enkelt",
          "DC 10: Enkelt",
          "DC 15: Medium (standard)",
          "DC 20: Vanskelig",
          "DC 25: Veldig vanskelig",
          "DC 30: Nesten umulig",
          "",
          "Tip: Bruk DC 15 som default.",
          "Gi adv/dis for modifikasjoner",
          "heller enn å justere DC.",
        ]),
        ("Heroic Inspiration", [
          "2024-regel (erstatter gamle Inspiration).",
          "",
          "Gis for:",
          "  Godt rollespill",
          "  Kreativ løsning",
          "  Nat 1 på d20 (2024-tillegg)",
          "",
          "Bruk: Rull på nytt ETT d20-kast.",
          "  Må bruke det nye resultatet.",
          "",
          "Maks 1 inspirasjon om gangen.",
          "Kan gis til andre spillere.",
        ]),
        ("Critical Success & Failure", [
          "Nat 20 på attack roll:",
          "  Automatisk treff.",
          "  Doble skade-terninger (ikke mod).",
          "  Eks: 2d6+3 blir 4d6+3",
          "",
          "Nat 1 på attack roll:",
          "  Automatisk bom.",
          "",
          "NB: Crit/fumble gjelder KUN",
          "angrepsruller, ikke ability checks",
          "eller saving throws.",
        ]),
      ]),

      ("Kamprunde", "", [
        ("Initiativ", [
          "Alle ruller d20 + DEX mod.",
          "Høyest går først.",
          "",
          "Ved likt:",
          "  PC vs PC: spillerne bestemmer",
          "  PC vs NPC: PC vinner",
          "  NPC vs NPC: DM velger",
          "",
          "Gruppe-initiativ (valgfritt):",
          "  Rull 1 kast for hele gruppen.",
          "  Raskere ved mange fiender.",
          "",
          "Surprise (2024):",
          "  Stealth vs Passive Perception.",
          "  Taper = disadvantage på initiativ.",
        ]),
        ("Turnstruktur", [
          "Per tur:",
          "  1 Action",
          "  1 Bonus Action (hvis tilgjengelig)",
          "  Movement (opp til Speed)",
          "  Gratis objekt-interaksjon",
          "  Tale (gratis)",
          "",
          "Per runde (ikke per tur):",
          "  1 Reaction",
          "",
          "Movement kan deles opp mellom,",
          "før og etter actions.",
        ]),
        ("Standard Actions", [
          "Attack: 1+ angrep (hvis Extra Attack)",
          "Cast a Spell: fulgt av spell-tiden",
          "Dash: dobbel movement",
          "Disengage: unngår opportunity attack",
          "Dodge: dis på angrep mot deg,",
          "  adv på DEX saves",
          "Help: allierte får adv ved neste kast",
          "Hide: Stealth-check",
          "Ready: forbered action + trigger",
          "Search: Perception/Investigation-check",
          "Use Object: bruk en gjenstand",
          "",
          "2024-tillegg:",
          "  Study: Investigation-check",
          "  Influence: sosial interaksjon",
          "  Magic: ikke-spell magisk handling",
        ]),
        ("Opportunity Attacks", [
          "Utløses når en fiende:",
          "  Forlater din reach",
          "  UTEN å bruke Disengage",
          "  UTEN å teleportere",
          "",
          "Bruker din Reaction.",
          "1 angrep med melee-våpen.",
          "",
          "Difficult terrain hindrer IKKE",
          "opportunity attacks.",
        ]),
        ("Reaksjoner", [
          "Kun 1 reaction per runde.",
          "Resettes ved starten av din tur.",
          "",
          "Vanlige reactions:",
          "  Opportunity Attack",
          "  Shield (spell)",
          "  Counterspell",
          "  Feather Fall",
          "  Ready'd action's trigger",
          "",
          "Interrupt vs Response:",
          "  Shield: FOER skade regnes",
          "  Hellish Rebuke: ETTER skade",
        ]),
      ]),

      ("Angrep & Skade", "", [
        ("Angrepsruller", [
          "Melee: d20 + STR mod + prof",
          "Ranged: d20 + DEX mod + prof",
          "Finesse: velg STR eller DEX",
          "",
          "Spell attack: d20 + spell mod + prof",
          "  (INT/WIS/CHA avh. av klasse)",
          "",
          "Treffer hvis:",
          "  Resultat >= mål sin AC",
          "",
          "Unarmed Strike:",
          "  1 + STR mod skade",
          "  Eller: grapple/shove (2024)",
        ]),
        ("Skade & Critical", [
          "Skade = våpenterninger + ability mod",
          "",
          "Critical hit:",
          "  Doble skade-terninger",
          "  Ikke doble modifikatorer",
          "  Eks: 1d8+3 -> 2d8+3",
          "",
          "Skadetyper:",
          "  Bludgeoning, Piercing, Slashing",
          "  Fire, Cold, Lightning, Thunder",
          "  Acid, Poison, Necrotic, Radiant",
          "  Psychic, Force",
          "",
          "Resistance: halv skade",
          "Vulnerability: dobbel skade",
          "Immunity: ingen skade",
        ]),
        ("Saving Throws", [
          "d20 + ability mod + prof (hvis trent)",
          "vs Save DC.",
          "",
          "Spell save DC = 8 + prof + spell mod",
          "",
          "Vanlige spell-saves:",
          "  Fireball: DEX, half on save",
          "  Hold Person: WIS, ingen effekt",
          "  Sleep: ingen save (HP-basert)",
          "",
          "Generelt ved save:",
          "  Fail = full effekt/skade",
          "  Pass = halv skade ELLER",
          "    ingen effekt (avh. av spell)",
        ]),
        ("Cover", [
          "Half Cover:",
          "  +2 AC",
          "  +2 DEX saves",
          "  (hjørne, liten stein)",
          "",
          "Three-Quarters Cover:",
          "  +5 AC",
          "  +5 DEX saves",
          "  (skytehull, tre)",
          "",
          "Total Cover:",
          "  Kan ikke angripes direkte",
          "  (vegg, stor stein)",
          "",
          "NB: Alliertes kropp gir IKKE cover",
          "med mindre de er mye større.",
        ]),
        ("Dying & Death", [
          "HP 0: Unconscious, Dying.",
          "",
          "Death Saving Throw:",
          "  d20 (ingen modifikator)",
          "  10+ = suksess",
          "  <10 = mislykket",
          "  Nat 20 = gjenvinn 1 HP",
          "  Nat 1 = 2 mislykkede",
          "",
          "3 suksesser = stabilisert",
          "3 mislykkede = død",
          "",
          "Skade mens dying:",
          "  = 1 mislykket save",
          "  Crit = 2 mislykkede",
          "  Skade >= max HP = insta-død",
          "",
          "Massive damage:",
          "  Tap HP >= max HP i et slag",
          "  CON save DC 15 eller død.",
        ]),
      ]),

      ("Conditions", "", [
        ("Oversikt (2024)", [
          "15 standard conditions:",
          "",
          "  Blinded     Incapacitated",
          "  Charmed     Invisible",
          "  Deafened    Paralyzed",
          "  Frightened  Petrified",
          "  Grappled    Poisoned",
          "  Prone       Restrained",
          "  Stunned     Unconscious",
          "  Exhaustion (1-10 nivåer)",
          "",
          "Conditions stacker IKKE,",
          "men flere forskjellige kan gjelde.",
        ]),
        ("Blinded / Deafened", [
          "Blinded:",
          "  Dis på angrep (du)",
          "  Adv på angrep (mot deg)",
          "  Sight-baserte checks = auto-fail",
          "",
          "Deafened:",
          "  Hearing-checks = auto-fail",
          "  Ingen kamp-effekt direkte",
        ]),
        ("Charmed / Frightened", [
          "Charmed:",
          "  Kan ikke angripe charmer",
          "  Charmer har adv på sosiale checks",
          "",
          "Frightened:",
          "  Dis på checks/attacks",
          "  mens kilden er synlig",
          "  Kan ikke bevege seg mot kilden",
        ]),
        ("Grappled / Restrained / Prone", [
          "Grappled:",
          "  Speed = 0",
          "  Ender når grappler incapacitated",
          "  Bryt fri: Athletics/Acrobatics",
          "    vs grapplerens DC",
          "",
          "Restrained:",
          "  Speed = 0",
          "  Dis på angrep (du)",
          "  Adv på angrep (mot deg)",
          "  Dis på DEX saves",
          "",
          "Prone:",
          "  Crawl eller stå opp (halv move)",
          "  Dis på angrep (du)",
          "  Adv på melee (mot deg)",
          "  Dis på ranged (mot deg)",
        ]),
        ("Stunned / Paralyzed / Unconscious", [
          "Stunned:",
          "  Incapacitated",
          "  Kan ikke bevege seg",
          "  Auto-fail STR/DEX saves",
          "  Adv på angrep (mot deg)",
          "",
          "Paralyzed:",
          "  Som Stunned PLUSS:",
          "  Melee-angrep = auto-crit",
          "  på 5 feet eller nærmere.",
          "",
          "Unconscious:",
          "  Som Paralyzed PLUSS:",
          "  Droper alt, faller prone.",
          "  Bevisstløs = vet ikke omgivelser.",
        ]),
        ("Petrified / Poisoned / Invisible", [
          "Petrified:",
          "  Forvandlet til stein.",
          "  Alt stopper, resistance mot alle.",
          "  Immun mot poison og sykdom.",
          "",
          "Poisoned:",
          "  Dis på angrep og ability checks.",
          "",
          "Invisible (2024):",
          "  Kan ikke sees (utenom spesielle).",
          "  Du har adv på angrep.",
          "  Angrep mot deg har dis.",
        ]),
        ("Exhaustion (2024)", [
          "1-10 nivåer. Hver nivå:",
          "  -2 på ALLE d20-kast",
          "  -2 feet Speed per level",
          "",
          "Nivå 10 = død.",
          "",
          "Long rest fjerner 1 level.",
          "Greater Restoration fjerner 1.",
          "",
          "Vanlige kilder:",
          "  Gå uten long rest i 24+ timer",
          "  Noen monstres angrep",
          "  Feile CON save ved tvunget marsj",
        ]),
      ]),

      ("Hvile & Healing", "", [
        ("Short Rest (1 time)", [
          "Spillerne kan:",
          "  Bruke Hit Dice for healing",
          "  Rull 1d(hit die) + CON mod",
          "  Gjenvinn brukte ressurser",
          "    (avh. av klasse)",
          "",
          "Klasser som trenger short rest:",
          "  Warlock (spell slots)",
          "  Monk (Ki)",
          "  Fighter (Action Surge)",
          "",
          "Anbefalt: 2 short rests per dag.",
        ]),
        ("Long Rest (8 timer)", [
          "Minst 6 timer søvn + 2 timer vakt.",
          "",
          "Gjenvinn:",
          "  Alle HP",
          "  Halvparten av max Hit Dice",
          "    (minimum 1)",
          "  Alle spell slots",
          "  Klasse-ressurser",
          "  -1 Exhaustion nivå",
          "",
          "Maks 1 long rest per 24 timer.",
          "Avbrudd (1+ time kamp) = ingen rest.",
          "",
          "Gritty realism (variant):",
          "  Short rest = natten",
          "  Long rest = 1 uke",
        ]),
        ("Healing", [
          "Cure Wounds: 1d8 + spell mod",
          "Healing Word: 1d4 + mod (bonus action)",
          "Potion of Healing: 2d4+2",
          "",
          "Healer's Kit:",
          "  Stabiliserer dying auto.",
          "  10 bruk per kit.",
          "",
          "Temporary HP:",
          "  Stacker IKKE - høyeste gjelder.",
          "  Forsvinner etter long rest.",
        ]),
      ]),

      ("Magi", "", [
        ("Spell Slots", [
          "Spell level != character level.",
          "",
          "Slot-tabell (full caster):",
          "  Lv 1:  2x L1",
          "  Lv 3:  4x L1, 2x L2",
          "  Lv 5:  4x L1, 3x L2, 2x L3",
          "  Lv 11: legger til L6",
          "  Lv 17: legger til L9",
          "",
          "Half caster (paladin, ranger):",
          "  Maks slot level = (lv + 1) / 2",
          "",
          "Cantrips (L0):",
          "  Ubegrenset bruk.",
          "  Skalerer på level 5, 11, 17.",
        ]),
        ("Spell Components", [
          "Verbal (V): må kunne snakke.",
          "  Silenced, gagged = kan ikke.",
          "",
          "Somatic (S): må ha 1 hånd fri.",
          "  Kan kombineres med focus/material.",
          "",
          "Material (M): spesifikt objekt",
          "  eller Component Pouch/Focus.",
          "  M med kostnad kan IKKE erstattes.",
          "  (eks: Resurrection = 1000 gp)",
          "",
          "Ritual (R): +10 min casting.",
          "  Forbruker IKKE spell slot.",
          "  Kun klasser med ritual casting.",
        ]),
        ("Concentration", [
          "Maks 1 konsentrasjons-spell.",
          "Ny conc = avslutter forrige.",
          "",
          "Brudd på concentration:",
          "  Tar skade: CON save",
          "  DC = max(10, skade/2)",
          "  Incapacitated: auto-bryter",
          "  Død: auto-bryter",
          "  Miljøeffekter (bølger osv.)",
          "",
          "War Caster feat: adv på save.",
          "",
          "Vanlige conc-spells:",
          "  Bless, Hold Person, Haste",
          "  Hunter's Mark, Spirit Guardians",
          "  Wall of Force, Polymorph",
        ]),
        ("Counterspell (2024)", [
          "Reaction når noen caster spell",
          "innen 60 feet som du ser.",
          "",
          "2024-regler:",
          "  Target caster tar CON save.",
          "  DC = 8 + prof + spell mod",
          "  Fail: spell fizzles, slot tapt.",
          "  Pass: spell virker normalt.",
          "",
          "Ved bruk av høyere slot:",
          "  Caster har dis på save.",
          "  (L4+ slot)",
        ]),
        ("Spellcasting Combat", [
          "Kaste cantrip + bonus action spell:",
          "  Tillatt (begge kan kastes)",
          "",
          "Kaste 2 non-cantrip spells i 1 tur:",
          "  IKKE tillatt (2024-regel).",
          "  Unntak: bonus action + cantrip.",
          "",
          "Spell attack vs AC: ingen save.",
          "Spell DC vs save: ingen attack.",
          "Omrade-spells: alle i området saves.",
          "",
          "Friendly fire (som Fireball):",
          "  JA, alle i området saves.",
        ]),
      ]),

      ("Utforskning", "", [
        ("Passive Scores", [
          "Passive = 10 + modifikator.",
          "",
          "Brukes for:",
          "  Passive Perception -",
          "    Oppdage skjulte ting,",
          "    motstå Stealth.",
          "  Passive Investigation -",
          "    Legge merke til spor.",
          "",
          "Advantage: +5 til passive.",
          "Disadvantage: -5 fra passive.",
          "",
          "DM avgjør om rull vs passive",
          "brukes - normalt passive først.",
        ]),
        ("Stealth", [
          "Stealth vs Passive Perception.",
          "",
          "Kan ikke gjemme seg fra noen som",
          "ser deg klart.",
          "",
          "Lightly obscured: dis på Perception.",
          "  (gjerne dim lys, svake skyer)",
          "",
          "Heavily obscured: ikke se.",
          "  (mørke, tåke)",
          "",
          "Invisible != Hidden:",
          "  Usynlig må fortsatt Stealth-rulle",
          "  for å være skjult.",
          "  Lyd/spor kan avsløre.",
        ]),
        ("Travel Pace", [
          "Slow: 2 mph,  18 miles/dag",
          "  Adv på Stealth",
          "",
          "Normal: 3 mph, 24 miles/dag",
          "  Standard",
          "",
          "Fast: 4 mph, 30 miles/dag",
          "  -5 passive Perception",
          "",
          "Forced march (8+ timer):",
          "  CON save DC 10 + 1/time",
          "  Fail = 1 exhaustion.",
        ]),
        ("Falling", [
          "1d6 skade per 10 feet.",
          "Max 20d6 (200 feet).",
          "",
          "Lander prone.",
          "",
          "Feather Fall:",
          "  Reaction, ingen skade, 60ft.",
          "",
          "Acrobatics-check for kontrollert",
          "fall (DM bestemmer).",
        ]),
        ("Climbing / Swimming", [
          "Koster dobbelt movement.",
          "  (1 ft climb = 2 ft speed)",
          "",
          "Athletics check:",
          "  Enkel vegg (greiper): ingen rull",
          "  Glatt vegg: DC 15+",
          "  Kraftig større belastning: dis",
          "",
          "Svømming i sterk strøm:",
          "  DC 10-20 avh. av strøm",
          "  Fail = fanget, tas nedover.",
        ]),
        ("Vision & Light", [
          "Bright Light: normalt syn.",
          "",
          "Dim Light (skumring):",
          "  Lightly obscured.",
          "  Dis på sight Perception.",
          "",
          "Darkness:",
          "  Heavily obscured.",
          "  Effektivt blinded.",
          "",
          "Darkvision (60 feet vanlig):",
          "  Dim i stedet for darkness.",
          "  Bright i stedet for dim.",
          "  Kun svart-hvitt.",
        ]),
      ]),

      ("Sosialt", "", [
        ("Sosiale checks", [
          "Persuasion: forhandle, oppriktig.",
          "Deception: lyve, bedra.",
          "Intimidation: true, skremme.",
          "Insight: lese folk.",
          "Performance: underholde.",
          "",
          "DM-tips:",
          "  La spillerne snakke først.",
          "  Be om rull kun ved tvil.",
          "  Godt rollespill kan senke DC.",
          "",
          "NPC-holdning (start):",
          "  Fiendtlig, Indifferent, Vennlig.",
          "  Bestemmer DC for påvirkning.",
        ]),
        ("Influence (2024)", [
          "2024-regler for sosial påvirkning:",
          "",
          "1. Beskriv hva du vil oppnå.",
          "2. DM setter DC basert på:",
          "   - NPC-holdning (Friendly DC 10,",
          "     Indifferent 15, Hostile 20)",
          "   - Hvor mye du ber om",
          "3. Rull Persuasion/Deception/",
          "   Intimidation/Performance.",
          "",
          "Fail =/= kategorisk nei.",
          "Kan gi counter-tilbud.",
        ]),
        ("Lie Detection", [
          "Insight (WIS) vs Deception (CHA).",
          "",
          "DM bestemmer:",
          "  Contested roll (begge ruller),",
          "  ELLER Insight vs Passive Deception.",
          "",
          "Hvordan kommunisere resultat:",
          "  Pass: 'Du tror hun lyver'",
          "  Fail: 'Hun virker ærlig'",
          "  (Ikke: 'hun lyver' direkte)",
        ]),
      ]),

      ("Encounter Design", "", [
        ("CR vs Level", [
          "Challenge Rating (CR) =",
          "  Hva 4 spillere på det level",
          "  kan håndtere ryddig.",
          "",
          "Deadly monster =",
          "  CR >= party level.",
          "",
          "Hurtig guide (per PC):",
          "  Easy:     CR party_lv / 4",
          "  Medium:   CR party_lv / 2",
          "  Hard:     CR party_lv",
          "  Deadly:   CR party_lv * 1.5",
          "",
          "Flere svake vs få sterke:",
          "  6+ motstandere gir boost i",
          "  oppfattet vanskelighet.",
        ]),
        ("Encounter-budsjett (2024)", [
          "XP-budsjett per PC per encounter:",
          "",
          "  Lv 1:  50 XP",
          "  Lv 5:  500 XP",
          "  Lv 10: 2000 XP",
          "  Lv 15: 5000 XP",
          "  Lv 20: 15000 XP",
          "",
          "Multiplier ved mange fiender:",
          "  1 fiende:     x1",
          "  2 fiender:    x1.5",
          "  3-6 fiender:  x2",
          "  7-10 fiender: x2.5",
          "  11-14:        x3",
          "  15+:          x4",
          "",
          "Anbefalt: 6-8 medium per dag.",
        ]),
        ("Monster HP", [
          "Bruk average HP fra stat-blokk.",
          "  (Raskere enn å rulle)",
          "",
          "Juster for vanskelighet:",
          "  Svakere: bruk minimum",
          "  Sterkere: rull HP",
          "  Boss: bruk maksimum",
          "",
          "Bloodied (hjelpemiddel):",
          "  HP <= halvparten.",
          "  Beskriv visuelt.",
          "  Noen monstre får ny fase.",
        ]),
        ("Legendary & Lair Actions", [
          "Legendary Actions:",
          "  1-3 per runde (etter andres turer).",
          "  Velg fra monsters liste.",
          "  Brukes MELLOM PC-turer.",
          "  Resettes ved starten av monsters tur.",
          "",
          "Lair Actions:",
          "  Kun i monsterets lair.",
          "  Initiativ 20 (taper ties).",
          "  Velg en handling fra listen.",
          "",
          "Legendary Resistance:",
          "  3/dag: bypass failed save,",
          "  velg å lykkes i stedet.",
        ]),
      ]),

      ("DC-referanse", "", [
        ("Fysiske handlinger", [
          "STR (Athletics):",
          "  Bryt tredør:   DC 13",
          "  Bryt jerndør:   DC 20",
          "  Kaste tunge ting: varies",
          "",
          "Hopping:",
          "  Long jump: STR score (ft)",
          "  High jump: 3 + STR mod (ft)",
          "  Running start kreves.",
          "  Halv uten running.",
          "",
          "DEX (Acrobatics):",
          "  Balansere smalt: DC 10-15",
          "  Iskald bakke: DC 10",
          "  Gli fri fra grep: vs grappler",
          "",
          "Svømme mot strøm: DC 15-20",
          "Klatre vanskelig: DC 15-20",
        ]),
        ("Låser & feller", [
          "Thieves' Tools (DEX):",
          "  Enkel lås:       DC 10",
          "  Gjennomsnitt:     DC 15",
          "  God lås:         DC 20",
          "  Mesterlås:       DC 25",
          "",
          "Finne felle:",
          "  Passive Perception / Investigation",
          "  Lett skjult:      DC 10",
          "  Profesjonell:     DC 15-20",
          "  Magisk/dedly:     DC 20+",
          "",
          "Avvæpne felle:",
          "  Samme DC som oppdagelse",
          "  vanligvis + 5.",
        ]),
        ("Kunnskap", [
          "Arcana, History, Religion,",
          "Nature, Medicine:",
          "",
          "  Allmenn viten:    DC 10",
          "  Utdannet:         DC 15",
          "  Ekspert-niva:     DC 20",
          "  Esoterisk:        DC 25+",
          "",
          "Investigation (INT):",
          "  Lete rom grundig: DC 10-15",
          "  Finne hemmelig:   DC 15-20",
          "  Dype spor:        DC 20+",
          "",
          "Insight (WIS):",
          "  Tydelig humør:   DC 10",
          "  Godt skjult:      DC 15-20",
          "  Mesterløgner:    DC 20+",
        ]),
        ("Miljøskade", [
          "Falling: 1d6/10ft, max 20d6.",
          "Fire (liten): 1d10/tur.",
          "Fire (stor): 3d6-10d6/tur.",
          "Lava: 10d10/tur.",
          "",
          "Drowning:",
          "  Hold pusten: 1 + CON min",
          "  Deretter: drop til 0 HP",
          "  neste tur: død om ikke berget.",
          "",
          "Ekstreme temperaturer:",
          "  CON save DC 5 + 1 per time",
          "  Fail = 1 exhaustion.",
          "",
          "Suffocation:",
          "  1 + CON min, deretter 0 HP.",
        ]),
      ]),

      ("DM Tips", "", [
        ("Rulings > Rules", [
          "Regler er retningslinjer.",
          "Du bestemmer ved tvil.",
          "",
          "Ved ukjent situasjon:",
          "  1. Hva er rimelig?",
          "  2. Hvilken ability er relevant?",
          "  3. Sett DC (default 15).",
          "  4. Let spilleren rulle.",
          "",
          "Ikke la regel-diskusjoner",
          "bremse spillet. Rul nu,",
          "sjekk senere.",
          "",
          "Vær konsistent innen samme kampanje.",
        ]),
        ("Say Yes, with a Cost", [
          "I stedet for 'nei' eller 'fail':",
          "",
          "  'Ja, og...'  (bonus)",
          "  'Ja, men...' (komplikasjon)",
          "  'Nei, men...' (alternativ)",
          "",
          "Eksempel:",
          "  Spiller vil klatre over vegg.",
          "  Vanlig DM: 'Du feiler, 1d6 skade.'",
          "  Bedre: 'Du kommer opp, men",
          "    vaktene hører deg.'",
          "",
          "Gir konsekvenser, ikke dødpunkter.",
        ]),
        ("Rule of Cool", [
          "Hvis spiller foreslår noe",
          "kreativt og kult:",
          "",
          "  Gi adv i stedet for å si nei.",
          "  La det virke i rollespillet,",
          "  selv om reglene ikke dekker det.",
          "",
          "Eksempel:",
          "  Barbarian vil svinge i takbjelken",
          "  og sparke fiende ned.",
          "  -> Athletics-check, ekstra skade",
          "     ved suksess.",
          "",
          "Minneverdige øyeblikk > RAW.",
        ]),
        ("Pacing", [
          "Kamp:",
          "  Hold turer under 60 sek.",
          "  Vurder 6-sekunders regel-",
          "    forklaringer.",
          "  Forbered spillere på sin tur.",
          "",
          "Sosiale scener:",
          "  La spillere drive.",
          "  DM stiller motspørsmål.",
          "",
          "Utforskning:",
          "  Beskriv sansene: syn, lyd, lukt.",
          "  Ikke alt krever rull.",
          "  Bruk montasje for kjedelige deler.",
        ]),
        ("Terningregler", [
          "Rull åpent (foran skjermen):",
          "  Pro: tillit, drama.",
          "  Con: kan døde PCer uhensiktsmessig.",
          "",
          "Rull skjult (bak skjerm):",
          "  Pro: fleksibilitet,",
          "    kan fudge ved behov.",
          "  Con: kan bli vane,",
          "    reduserer spenning.",
          "",
          "Kompromiss:",
          "  Aapne attack rolls,",
          "  skjulte Perception/Insight",
          "  (spillerne vet ikke DC).",
        ]),
        ("Når å fudge", [
          "AVOID fudging i PC's disfavør.",
          "Det undergraver spilleragentur.",
          "",
          "OK-situasjoner:",
          "  Ferste kamp, PC blir utheldig",
          "    drept i turn 1: overveien",
          "  Final boss dør på crit turn 1:",
          "    gi ham en fase, ikke fudge HP.",
          "",
          "Bedre løsninger:",
          "  La monster droppe inconscious",
          "    i stedet for død.",
          "  NPC allierte kommer inn.",
          "  Cliffhangere, ikke insta-død.",
        ]),
      ]),

      ("Monster-oppslag", "", [
        ("Statblokk-lesing", [
          "Høyeste prioritet:",
          "  AC (Armor Class)",
          "  HP (Hit Points)",
          "  Speed",
          "  Abilities og modifiers",
          "",
          "Deretter:",
          "  Skills og Saves (trent)",
          "  Senses (darkvision etc.)",
          "  Languages",
          "  CR",
          "",
          "Handlinger:",
          "  Multiattack først!",
          "  Spell list (hvis caster)",
          "  Spesielle egenskaper",
          "",
          "Taktikk:",
          "  Hva vil monsteret?",
          "  Hva frykter det?",
          "  Flykter det ved halv HP?",
        ]),
        ("Monstertyper", [
          "Aberration: alien, psionisk",
          "Beast:      dyr, ikke-magisk",
          "Celestial:  engel, deva",
          "Construct:  golem, modron",
          "Dragon:     drage, kobold",
          "Elemental:  elemental, djinn",
          "Fey:        fae, dryad, satyr",
          "Fiend:      demon, devil",
          "Giant:      kjempe, ogre",
          "Humanoid:   menneske, orc, elf",
          "Monstrosity: owlbear, chimera",
          "Ooze:       slime, pudding",
          "Plant:      shambler, treant",
          "Undead:     zombie, vampyr",
          "",
          "Viktig for Turn Undead,",
          "Hunter's Mark, Favored Enemy etc.",
        ]),
        ("Kampadferd", [
          "Svakt monster (CR < party lv):",
          "  Flykter ved 25% HP.",
          "  Overgir seg om omringet.",
          "",
          "Dyr (uten intelligens):",
          "  Angriper nærmeste trussel.",
          "  Flykter ved smerte/frykt.",
          "",
          "Intelligent monster:",
          "  Fokuser squishy casters.",
          "  Bruker dekning, flanking.",
          "  Taktisk retrett.",
          "",
          "Boss/Solo:",
          "  Bruker miljøet.",
          "  Sparker casters først.",
          "  Utnytter svakheter.",
        ]),
      ]),

      ("Spell-referanse", "", [
        ("Cantrips (L0)", [
          "Vanlige offensive cantrips:",
          "",
          "Fire Bolt (V,S, 120ft):",
          "  Ranged spell atk, 1d10 fire.",
          "  Skalerer: 2d10 (lv5), 3d10 (lv11),",
          "  4d10 (lv17).",
          "",
          "Eldritch Blast (V,S, 120ft):",
          "  Ranged spell atk, 1d10 force.",
          "  Flere stråler ved høyere nivå.",
          "",
          "Sacred Flame (V,S, 60ft):",
          "  DEX save, 1d8 radiant, ingenting",
          "  ved suksess. Ignorerer cover.",
          "",
          "Toll the Dead (V,S, 60ft):",
          "  WIS save, 1d8 (1d12 hvis skadet).",
          "  Nekrotisk skade.",
          "",
          "Vicious Mockery (V, 60ft):",
          "  WIS save, 1d4 psychic + dis på",
          "  neste attack roll. Målet må høre.",
        ]),
        ("Cantrips - nyttige", [
          "Light (V,M, touch):",
          "  Gjenstand lyser i 20ft radius.",
          "",
          "Mage Hand (V,S, 30ft):",
          "  Usynlig hånd, bær opp til 10 lbs.",
          "",
          "Minor Illusion (S,M, 30ft):",
          "  Lyd ELLER bilde i 5ft kube.",
          "  Investigation for å avsløre.",
          "",
          "Prestidigitation (V,S, 10ft):",
          "  Små magiske effekter: varme",
          "  objekter, rengjøre, smake krydder.",
          "",
          "Guidance (V,S, touch):",
          "  +1d4 på valgfritt ability check",
          "  innen 1 minutt. Concentration.",
          "",
          "Thaumaturgy (V, 30ft):",
          "  Stemme tredobles, flamme flimrer,",
          "  dører slamrer, etc.",
        ]),
        ("Level 1 spells - vanlige", [
          "Shield (V,S, reaction):",
          "  +5 AC til neste tur.",
          "  Utløses når du blir truffet.",
          "",
          "Healing Word (V, bonus, 60ft):",
          "  1d4 + mod healing. Bonus action!",
          "",
          "Cure Wounds (V,S, touch):",
          "  1d8 + mod healing. Action.",
          "",
          "Magic Missile (V,S, 120ft):",
          "  3 darts à 1d4+1 force.",
          "  Automatisk treff. Skala: +1 dart",
          "  per høyere slot-nivå.",
          "",
          "Burning Hands (V,S, 15ft kjegle):",
          "  DEX save, 3d6 fire (halv ved save).",
          "",
          "Sleep (V,S,M, 90ft):",
          "  5d8 HP verdt fiender sovner.",
          "  Laveste HP først. Ingen save.",
        ]),
        ("Level 1 - kontroll & buff", [
          "Bless (V,S,M, 30ft, conc 1 min):",
          "  3 mål: +1d4 på atk rolls og saves.",
          "",
          "Faerie Fire (V, 60ft, conc 1 min):",
          "  DEX save, målene lyser opp.",
          "  Advantage på angrep mot dem.",
          "",
          "Hex (V,S,M, 90ft, conc 1 time):",
          "  Bonus action. +1d6 nekrotisk på",
          "  angrep. Dis på valgt ability.",
          "",
          "Hunter's Mark (V, 90ft, conc 1 time):",
          "  Bonus action. +1d6 på angrep",
          "  mot målet. Flyttes ved mål-drap.",
          "",
          "Thunderwave (V,S, 15ft kube):",
          "  CON save, 2d8 thunder + 10ft",
          "  skyv. Halv på save, ingen skyv.",
          "",
          "Detect Magic (V,S, ritual):",
          "  Sans magi innen 30ft i 10 min.",
        ]),
        ("Level 2-3 highlights", [
          "Misty Step (V, bonus, 30ft):",
          "  Teleporter. Bonus action.",
          "",
          "Shatter (V,S,M, 60ft, 10ft sfære):",
          "  CON save, 3d8 thunder.",
          "",
          "Hold Person (V,S,M, 60ft, conc 1 min):",
          "  WIS save, paralyzed. Save ved",
          "  slutten av hver tur.",
          "",
          "Web (V,S,M, 60ft, conc 1 time):",
          "  DEX save, restrained i 20ft kube.",
          "",
          "Fireball (V,S,M, 150ft, 20ft sfære):",
          "  DEX save, 8d6 fire (halv ved save).",
          "  Klassisk party-killer. PASS PÅ.",
          "",
          "Counterspell (S, reaction, 60ft):",
          "  Se egen counterspell-regel.",
          "",
          "Fly (V,S,M, touch, conc 10 min):",
          "  60ft flying speed.",
          "",
          "Haste (V,S,M, 30ft, conc 1 min):",
          "  +2 AC, +1 action, dobbel speed,",
          "  adv på DEX saves. Ved conc-brudd:",
          "  målet kan ikke handle i 1 tur.",
        ]),
        ("Higher level highlights", [
          "L4 - Greater Invisibility:",
          "  Du er usynlig selv når angrep.",
          "  Conc 1 min.",
          "",
          "L4 - Polymorph:",
          "  WIS save, målet blir en beast.",
          "  Brukes offensivt OG defensivt.",
          "",
          "L5 - Hold Monster: som Hold Person",
          "  men fungerer på alle.",
          "",
          "L5 - Cone of Cold: 8d8 cold i kjegle.",
          "",
          "L6 - Chain Lightning:",
          "  10d8 lightning, opp til 4 mål.",
          "",
          "L6 - True Seeing: se det skjulte.",
          "",
          "L7 - Teleport: instant reise.",
          "",
          "L8 - Dominate Monster:",
          "  Total kontroll ved failed WIS save.",
          "",
          "L9 - Wish: 8000 gp, hva du vil.",
          "  Spellcaster risikerer å ikke",
          "  kunne kaste Wish igjen.",
        ]),
      ]),

      ("Monsterreferanse", "", [
        ("CR-guide (Challenge Rating)", [
          "CR viser hvor tøft et monster er",
          "mot fire PC-er på tilsvarende nivå.",
          "",
          "Grov HP-guide per CR:",
          "  CR 1/8: 7-35 HP",
          "  CR 1/4: 36-49 HP",
          "  CR 1/2: 50-70 HP",
          "  CR 1:   71-85 HP",
          "  CR 2:   86-100 HP",
          "  CR 3:   101-115 HP",
          "  CR 5:   131-145 HP",
          "  CR 10:  206-220 HP",
          "  CR 15:  341-355 HP",
          "  CR 20:  476-490 HP",
          "",
          "AC-guide:",
          "  CR 1-4: AC 13-15",
          "  CR 5-10: AC 15-17",
          "  CR 11-16: AC 17-18",
          "  CR 17+: AC 18-19",
        ]),
        ("Typisk skade per CR", [
          "Total skade per runde:",
          "  CR 1:   5-10 skade",
          "  CR 3:   18-23",
          "  CR 5:   33-38",
          "  CR 10:  69-74",
          "  CR 15:  115-120",
          "  CR 20:  170-175",
          "",
          "Attack bonus per CR:",
          "  CR 1-3: +3 til +4",
          "  CR 4-7: +5 til +6",
          "  CR 8-12: +7 til +8",
          "  CR 13-16: +9 til +10",
          "  CR 17+: +11 eller mer",
          "",
          "Save DC:",
          "  CR 1-3: DC 13",
          "  CR 4-7: DC 14-15",
          "  CR 8-12: DC 16-17",
          "  CR 13+: DC 18-20",
        ]),
        ("Klassiske low-level fiender", [
          "Goblin (CR 1/4, AC 15, HP 7):",
          "  Scimitar 1d6+2, Shortbow 1d6+2.",
          "  Nimble Escape: bonus Disengage.",
          "",
          "Orc (CR 1/2, AC 13, HP 15):",
          "  Greataxe 1d12+3. Aggressive:",
          "  bonus move mot fiende.",
          "",
          "Hobgoblin (CR 1/2, AC 18, HP 11):",
          "  Longsword 1d8+1 eller Longbow.",
          "  Martial Advantage: +2d6 hvis",
          "  alliert innen 5ft av mål.",
          "",
          "Bandit (CR 1/8, AC 12, HP 11):",
          "  Scimitar 1d6+1, Crossbow 1d8+1.",
          "",
          "Skeleton (CR 1/4, AC 13, HP 13):",
          "  Shortsword 1d6+2, Shortbow 1d6+2.",
          "  Vulnerability: bludgeoning.",
          "",
          "Zombie (CR 1/4, AC 8, HP 22):",
          "  Slam 1d6+1. Undead Fortitude:",
          "  CON save DC 5+dmg for å overleve",
          "  med 1 HP (utenom radiant/crit).",
        ]),
        ("Mid-level fiender", [
          "Ogre (CR 2, AC 11, HP 59):",
          "  Greatclub 2d8+4, Javelin 2d6+4.",
          "",
          "Owlbear (CR 3, AC 13, HP 59):",
          "  Multiattack: Beak + Claws.",
          "  Beak 1d10+5, Claws 2d8+5.",
          "",
          "Knight (CR 3, AC 18, HP 52):",
          "  Greatsword 2d6+3, Heavy Crossbow.",
          "  Brave: adv vs frightened.",
          "",
          "Ettin (CR 4, AC 12, HP 85):",
          "  2 slag: Battleaxe 2d8+5, Morning-",
          "  star 2d8+5. Kan ikke overraskes.",
          "",
          "Troll (CR 5, AC 15, HP 84):",
          "  3 slag: 1 bite + 2 claws.",
          "  Regenererer 10 HP per tur hvis",
          "  ikke skadet av fire/acid.",
          "",
          "Hill Giant (CR 5, AC 13, HP 105):",
          "  2 slag: Greatclub 3d8+5 eller",
          "  Rock 3d10+5 (60ft).",
        ]),
        ("Drager (CR 4-17)", [
          "Young White (CR 6, AC 17, HP 133):",
          "  Breath DC 15 CON, 10d8 cold.",
          "",
          "Young Green (CR 8, AC 18, HP 136):",
          "  Breath DC 14 CON, 12d6 poison.",
          "",
          "Young Red (CR 10, AC 18, HP 178):",
          "  Breath DC 17 DEX, 16d6 fire.",
          "",
          "Adult Black (CR 14, AC 19, HP 195):",
          "  Legendary + Lair actions.",
          "",
          "Adult Red (CR 17, AC 19, HP 256):",
          "  Breath 26d6 fire. DC 21.",
          "",
          "Ancient (CR 20+): kun for level 17+",
          "parties. Separate sesjoner.",
          "",
          "Generelle dragetaktikker:",
          "- Drager bruker breath når flere",
          "  fiender er samlet (~recharge 5-6).",
          "- De flykter når halvparten HP.",
          "- Legendary resistance: 3/dag,",
          "  ignorerer failed save.",
        ]),
        ("Boss-monstre", [
          "Beholder (CR 13, AC 18, HP 180):",
          "  Eye rays - 3 per tur, tilfeldig.",
          "  Anti-magic cone fra hovedøyet.",
          "",
          "Lich (CR 21, AC 17, HP 135):",
          "  Full spellcaster opp til L9.",
          "  Rejuvenation: respawner i phylactery.",
          "",
          "Tarrasque (CR 30, AC 25, HP 676):",
          "  Ender kampanjer. Magisk immunitet",
          "  under 6. nivå. Kan ikke flykte fra.",
          "",
          "Pit Fiend (CR 20, AC 19, HP 300):",
          "  Legion i Nine Hells. Fireball DC 21.",
          "",
          "Demon Lord eksempler:",
          "  Demogorgon (CR 26)",
          "  Orcus (CR 26)",
          "  Graz'zt (CR 24)",
          "",
          "Husk: Boss-kamper trenger:",
          "- Minions (hindre fokusild)",
          "- Terreng som kan brukes",
          "- Faser (HP-thresholds)",
        ]),
      ]),

      ("Skatt & belønning", "", [
        ("XP per encounter", [
          "Enkel guide: del monsterets CR-XP",
          "på antall PC-er.",
          "",
          "XP per CR:",
          "  CR 1/8: 25 XP",
          "  CR 1/4: 50 XP",
          "  CR 1/2: 100 XP",
          "  CR 1:   200 XP",
          "  CR 2:   450 XP",
          "  CR 3:   700 XP",
          "  CR 4:   1100 XP",
          "  CR 5:   1800 XP",
          "  CR 10:  5900 XP",
          "  CR 15:  13000 XP",
          "  CR 20:  25000 XP",
          "",
          "XP-grenser for opplevelsesnivå:",
          "  Lv 2: 300 XP",
          "  Lv 3: 900 XP",
          "  Lv 5: 6500 XP",
          "  Lv 10: 64000 XP",
          "  Lv 15: 195000 XP",
          "",
          "Alternativ: milestone leveling",
          "(bestem du når de går opp).",
        ]),
        ("Gullbelønning per nivå", [
          "Omtrentlig per karakter:",
          "  Lv 1-4: 25-300 gp per session",
          "  Lv 5-10: 300-2500 gp",
          "  Lv 11-16: 2500-20000 gp",
          "  Lv 17-20: 20000+ gp",
          "",
          "Typisk loot-fordeling:",
          "  Mynter (cp/sp/gp)",
          "  Edelstener / smykker",
          "  Kunstgjenstander",
          "  Magiske gjenstander",
          "  Pergamenter / formler",
          "",
          "Rollespill-regel:",
          "  Lar karakterene gå på jakt etter",
          "  spesifikt loot de har et mål for.",
        ]),
        ("Magiske gjenstander - rarity", [
          "Common: 50-100 gp",
          "  Potion of Healing, +1 ammo",
          "",
          "Uncommon: 101-500 gp",
          "  +1 våpen/rustning, Bag of Holding,",
          "  Wand of Magic Missiles",
          "",
          "Rare: 501-5000 gp",
          "  +2 våpen/rustning, Flame Tongue,",
          "  Boots of Speed",
          "",
          "Very Rare: 5001-50000 gp",
          "  +3 våpen, Holy Avenger,",
          "  Staff of Power",
          "",
          "Legendary: 50001+ gp",
          "  Vorpal Sword, Holy Avenger,",
          "  Staff of the Magi",
          "",
          "Attunement: maks 3 per karakter.",
          "Short rest å tune in (1 time fokus).",
        ]),
        ("Anbefalte gjenstander per nivå", [
          "Lv 1-4 (low magic):",
          "  1-2 common/uncommon per PC.",
          "  Healing potions, +1 våpen",
          "",
          "Lv 5-10 (mid magic):",
          "  1 rare per PC, flere uncommon.",
          "  +1 våpen/rustning standard.",
          "",
          "Lv 11-16 (high magic):",
          "  1-2 rare + 1 very rare per PC.",
          "  +2 gear, spesialiserte items.",
          "",
          "Lv 17-20 (epic):",
          "  1 legendary + flere very rare.",
          "  +3 gear, artefakt-lignende.",
          "",
          "Merknad: Attunement-slot er",
          "begrensningen. 3 slots per PC.",
        ]),
        ("Hurtige loot-tabeller", [
          "Liten lommebok (CR 0-4):",
          "  2d6 sp, 1d6 gp,",
          "  50% en common-gjenstand.",
          "",
          "Bandit-leder (CR 1-4):",
          "  3d6 gp, +1 våpen 20% sjanse",
          "",
          "Hoard (CR 5-10):",
          "  2d6×100 sp, 1d6×100 gp,",
          "  4d6×10 gp i edelstener,",
          "  1d6 uncommon magic items,",
          "  20%: 1 rare item",
          "",
          "Drage-hoard (CR 11-16):",
          "  1d3×1000 gp, 1d6×100 pp,",
          "  2d6 uncommon + 1d6 rare,",
          "  1-2 very rare items.",
        ]),
      ]),

      ("Verden & reise", "", [
        ("Avstander", [
          "1 square = 5 feet (1,5 m) i kamp.",
          "",
          "Normal speed per runde (6 sek):",
          "  25ft = sakte (dverg med rustning)",
          "  30ft = standard (menneske)",
          "  35ft = rask (elf, halfling)",
          "  40ft+ = svært rask",
          "",
          "Overland reise (se Travel Pace).",
          "",
          "Vanlige distanser:",
          "  Bueskudd: 80-600 ft",
          "  Siktvidde utendørs: 1-2 miles",
          "  Dag-marsj: 24 miles normal",
          "  Fjerde tider så langt til hest.",
        ]),
        ("Proviant & forsyninger", [
          "Normal karakter trenger per dag:",
          "  Mat: 1 lb (0,5 kg)",
          "  Vann: 1 gallon (ca 4 L)",
          "",
          "I varmt klima: 2 ganger vann.",
          "Rasjoner holder seg:",
          "  Trail rations: flere uker",
          "  Fersk mat: 1-3 dager",
          "",
          "Jakt/Foraging:",
          "  Survival DC 10 (normalt),",
          "  15 (ørken/frost),",
          "  20 (magiske områder).",
          "  Skaffer mat for 1d6+mod personer.",
          "",
          "Uten mat: 1 exhaustion etter",
          "3+CON mod dager.",
        ]),
        ("Været", [
          "Vindkastestyrker:",
          "  Strong wind (20+ mph):",
          "    Dis på ranged attacks",
          "    Slokker åpne flammer",
          "    Dis på Perception (hørsel)",
          "  Heavy rain/storm:",
          "    Heavily obscured ved langdistanse",
          "    Dis på Perception (syn)",
          "",
          "Temperatur:",
          "  Ekstremt kaldt: CON save DC 10",
          "    per time uten klær.",
          "    Fail = 1 exhaustion.",
          "  Ekstremt varmt: samme DC,",
          "    men øker hver time.",
          "",
          "Tynn luft (høyfjell):",
          "  Double trening-kostnad,",
          "  1 exhaustion etter 4 timer.",
        ]),
        ("Handel & tjenester", [
          "Typiske priser:",
          "  Måltid (taverne):     1-5 sp",
          "  Dagens overnatting:   5 sp - 2 gp",
          "  Gjestgiveri (uke):    7-14 gp",
          "",
          "  Hest (ridehest):      75 gp",
          "  Krigshest:            400 gp",
          "  Vogn:                 100 gp",
          "  Båt (mindre):         1000+ gp",
          "",
          "Daglig hire:",
          "  Butler/tjener:        2 sp/dag",
          "  Vaktmann:             2-5 sp/dag",
          "  Leiesoldat:           2 gp/dag",
          "  Spion:                10-20 gp",
          "  Skipskaptein:         10 gp/dag",
          "",
          "Gildets kostnad (inflasjon 10x):",
          "  Svært sjelden gjenstand:",
          "  10-100× boknotert pris.",
        ]),
        ("Downtime-aktiviteter", [
          "Mellom eventyr (per uke):",
          "",
          "Profession:",
          "  Bruk tool proficiency,",
          "  tjen 1d10+mod gp per uke.",
          "",
          "Training (nytt språk/tool):",
          "  10 uker, 1 gp/dag (≈70 gp).",
          "",
          "Crafting:",
          "  Halv markedspris i material.",
          "  5 gp produksjon per dag.",
          "",
          "Research:",
          "  Finn fakta. DC 10+. 1 gp/dag.",
          "  Bibliotek eller ekspert.",
          "",
          "Carousing (sosialt):",
          "  Knyt bånd, høre rykter.",
          "  Kostnad varierer med klasse.",
          "",
          "Recuperating:",
          "  3 dager long rests helbreder",
          "  sykdom/gift (CON save).",
        ]),
      ]),

      ("Kampanje-verktøy", "", [
        ("Session zero", [
          "Før spillet begynner:",
          "",
          "  Safety tools: lines & veils",
          "  (hva er OK/ikke OK i spillet).",
          "",
          "  Tone & sjanger: heroic? horror?",
          "  political intrigue?",
          "",
          "  House rules: homebrew, flanking,",
          "  crit-regler, rest-variants.",
          "",
          "  Spilleragenter: hva forventes",
          "  av spillerne? scheduling?",
          "",
          "  Karakterkonsept-runde: hver spiller",
          "  forklarer kort hva de ønsker.",
          "",
          "  Party hook: hvorfor er dere samlet?",
        ]),
        ("Running a session", [
          "Struktur for en 3-timers session:",
          "",
          "  Oppsummering (5 min):",
          "    Forrige gang, sist scene.",
          "",
          "  Scene 1 - sosial (30-45 min):",
          "    Rollespill, info-innsamling.",
          "",
          "  Utforskning (20-30 min):",
          "    Reise, miljø, oppdagelser.",
          "",
          "  Scene 2 - kamp/utfordring (45 min):",
          "    Hovedhendelse.",
          "",
          "  Downtime/loot (15 min):",
          "    Gjennomgang, level-up.",
          "",
          "  Cliffhanger (siste 10 min):",
          "    Ny trussel eller oppdagelse.",
          "",
          "Pauser: hver 60-90 min, 10-15 min.",
        ]),
        ("Improv-verktøy", [
          "Når spillerne går uventet retning:",
          "",
          "NPC quick-gen:",
          "  1 personlighetstrekk (vennlig/mutt)",
          "  1 særegenhet (hår, aksent, tick)",
          "  1 motivasjon (penger, hevn, familie)",
          "  1 hemmelighet",
          "",
          "Navn-banker (forhåndsgenerert):",
          "  Menneske: Aldric, Bryn, Cora...",
          "  Alvisk: Aelar, Lysanthir, Meriele...",
          "  Dvergisk: Morgran, Brottor, Dain...",
          "",
          "Sted-quick:",
          "  1 dominerende farge",
          "  1 lukt",
          "  1 lyd",
          "  1 uvanlig detalj",
          "",
          "Plot-twist-generator:",
          "  Allierte er ikke som de virker",
          "  Fiendens virkelige mål avsløres",
          "  En NPC fra fortiden dukker opp",
        ]),
        ("Problem-situasjoner", [
          "Spiller overskrider grenser:",
          "  Pause, snakk utenfor spillet.",
          "  Referer til session zero.",
          "",
          "Spiller overdriver:",
          "  'Det var min rolle!' - svar",
          "  diplomatisk men tydelig.",
          "",
          "Spiller er stille/tilbaketrukket:",
          "  Spør direkte: 'Hva gjør X?'",
          "  Gi dem øyeblikk de kan skinne.",
          "",
          "Spillere er uenige:",
          "  La dem debattere 5 min.",
          "  Så: karakterene må bestemme,",
          "  ikke spillerne.",
          "",
          "Party splitter seg:",
          "  Kort scene for hver gruppe.",
          "  Hold det korte og enkelt.",
          "",
          "TPK (total party kill):",
          "  Forbered backup-plan:",
          "  fanget, reddet av NPC, o.l.",
        ]),
        ("Level-up håndtering", [
          "Hver gang PC går opp i nivå:",
          "",
          "1. HP:",
          "   Enten ruller ny HD + CON mod,",
          "   eller tar snittverdien (HDsnitt).",
          "",
          "2. Spells:",
          "   Nye slots tilgjengelige.",
          "   Kan bytte ut prepared spells.",
          "   Nye known spells (avh. av klasse).",
          "",
          "3. Nye features:",
          "   Se klasse-tabellen.",
          "   Eks: Extra Attack (lv 5 fighter).",
          "",
          "4. Proficiency Bonus:",
          "   Oppdateres ved lv 5, 9, 13, 17.",
          "",
          "5. Ability Score Improvement (ASI):",
          "   Vanligvis lv 4, 8, 12, 16, 19.",
          "   +2 til én eller +1 til to.",
          "   Eller velg en Feat i stedet.",
          "",
          "Anbefaling: level-up hjemme,",
          "ikke i kampanjen.",
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

    # =========================================================
    # LayerPlayer: én MediaPlayer-instans per loop-boks i scene.
    # Flere LayerPlayer kan kjøre parallelt – hver med eget volum.
    # Spiller både lokale filer og URLer (Internet Archive). Looper.
    # =========================================================
    class LayerPlayer:
        def __init__(self):
            self.mp = None
            self.is_playing = False
            self._v = 0.7
            self._loop = True
            self._src = None
            self._is_url = False

        def play(self, source, is_url=False, loop=True):
            self.stop()
            self._src = source
            self._is_url = is_url
            self._loop = loop
            if USE_JNIUS:
                def _s():
                    try:
                        mp = MediaPlayer()
                        mp.setDataSource(source)
                        mp.setVolume(self._v, self._v)
                        try: mp.setLooping(loop)
                        except: pass
                        mp.prepare()
                        mp.start()
                        self.mp = mp
                        self.is_playing = True
                        log(f"Layer OK: {source[:60]}")
                    except Exception as e:
                        log(f"Layer err: {e}")
                        self.is_playing = False
                # URLer trenger thread; lokale filer raskt – men gjør det likt
                threading.Thread(target=_s, daemon=True).start()
                return True
            # Fallback (desktop): Kivy SoundLoader (kun lokale filer)
            if not is_url:
                try:
                    from kivy.core.audio import SoundLoader
                    self.mp = SoundLoader.load(source)
                    if self.mp:
                        self.mp.volume = self._v
                        self.mp.loop = loop
                        self.mp.play()
                        self.is_playing = True
                        return True
                except Exception as e:
                    log(f"Layer fallback err: {e}")
            return False

        def stop(self):
            if self.mp:
                try:
                    if USE_JNIUS:
                        try:
                            if self.mp.isPlaying():
                                self.mp.stop()
                        except: pass
                        try: self.mp.release()
                        except: pass
                    else:
                        try: self.mp.stop()
                        except: pass
                except:
                    pass
                self.mp = None
            self.is_playing = False

        def vol(self, v):
            self._v = v
            if not self.mp:
                return
            try:
                if USE_JNIUS:
                    self.mp.setVolume(v, v)
                else:
                    self.mp.volume = v
            except:
                pass

    # =========================================================
    # OneShotPlayer: fyrer av korte lyder (lokale filer).
    # Hver avfyring lager en ny MediaPlayer og frigjør ressurser
    # automatisk når lyden er ferdig (cleanup-tick). Tillater
    # mange overlappende oneshots samtidig.
    # =========================================================
    class OneShotPlayer:
        def __init__(self):
            self._players = []   # liste av aktive MediaPlayer
            self._snds = []      # liste av aktive Kivy Sound (fallback)
            self._v = 0.8
            self._cleanup_running = False

        def fire(self, path):
            if not os.path.exists(path):
                log(f"oneshot mangler: {path}")
                return False
            if USE_JNIUS:
                try:
                    mp = MediaPlayer()
                    mp.setDataSource(path)
                    mp.setVolume(self._v, self._v)
                    mp.prepare()
                    mp.start()
                    self._players.append(mp)
                    self._ensure_cleanup()
                    return True
                except Exception as e:
                    log(f"oneshot err: {e}")
                    return False
            # Fallback (desktop)
            try:
                from kivy.core.audio import SoundLoader
                snd = SoundLoader.load(path)
                if snd:
                    snd.volume = self._v
                    snd.play()
                    self._snds.append(snd)
                    self._ensure_cleanup()
                    return True
            except Exception as e:
                log(f"oneshot fallback err: {e}")
            return False

        def _ensure_cleanup(self):
            if self._cleanup_running:
                return
            self._cleanup_running = True
            Clock.schedule_interval(self._cleanup, 1.5)

        def _cleanup(self, dt):
            # Android MediaPlayer
            for p in self._players[:]:
                try:
                    if not p.isPlaying():
                        try: p.release()
                        except: pass
                        self._players.remove(p)
                except:
                    try: self._players.remove(p)
                    except: pass
            # Kivy Sound fallback
            for s in self._snds[:]:
                try:
                    if s.state != 'play':
                        self._snds.remove(s)
                except:
                    try: self._snds.remove(s)
                    except: pass
            if not self._players and not self._snds:
                self._cleanup_running = False
                return False
            return True

        def stop_all(self):
            for p in self._players[:]:
                try:
                    if p.isPlaying(): p.stop()
                    p.release()
                except: pass
            self._players.clear()
            for s in self._snds[:]:
                try: s.stop()
                except: pass
            self._snds.clear()

        def vol(self, v):
            self._v = v

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
            self.oneshot = OneShotPlayer()
            self.cast = CastMgr()
            self.server = MediaServer()
            self.chars = load_json(CHAR_FILE, [])
            self.scenarios = load_json(SCENARIO_FILE, [])
            self.edit_idx = None
            # Scenario-state
            self._scn_view = 'list'      # 'list' | 'scenes' | 'editor'
            self._scn_idx = None         # aktiv scenario
            self._scn_scene_idx = None   # aktiv scene
            self._scn_layers = []        # liste av aktive LayerPlayer
            self._scn_box_widgets = []   # widget-refs for live oppdatering

            # FloatLayout som rot – lar oss legge splash oppå
            wrapper = FloatLayout()

            main = BoxLayout(orientation='vertical', spacing=0,
                             size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            main.add_widget(Widget(size_hint_y=None, height=dp(30)))

            # FANER
            tabs = RBox(size_hint_y=None, height=dp(52), spacing=dp(4),
                        padding=[dp(8), 0], bg_color=BTN)
            self._tabs = {}
            for key, txt in [('img','Bilder'),('lyd','Lyd'),('tool','Karakter'),('rules','Regler'),('cast','Cast')]:
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
                'img': self._mk_img, 'lyd': self._mk_lyd,
                'tool': self._mk_tool,
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

        # ---------- LYD (Musikk + Ambient + One-shot + Scenarier) ----------
        def _mk_lyd(self):
            """Lyd-fane med sub-tabs."""
            if not hasattr(self, '_lyd_sub'):
                self._lyd_sub = 'mus'

            p = BoxLayout(orientation='vertical', spacing=dp(6))

            # Sub-tab-rad
            sub_bar = RBox(size_hint_y=None, height=dp(42),
                           spacing=dp(4), padding=[dp(6), dp(4)],
                           bg_color=BTN, radius=dp(10))

            def _mk_sub(key, label):
                act = self._lyd_sub == key
                b = RToggle(
                    text=label, group='lyd_sub',
                    state='down' if act else 'normal',
                    bg_color=BTNH if act else BTN,
                    color=GOLD if act else DIM,
                    font_size=sp(11), bold=True)
                b.bind(on_release=lambda btn, k=key: self._lyd_switch(k))
                return b

            sub_bar.add_widget(_mk_sub('mus', 'Musikk'))
            sub_bar.add_widget(_mk_sub('amb', 'Ambient'))
            sub_bar.add_widget(_mk_sub('one', 'One-shot'))
            sub_bar.add_widget(_mk_sub('scn', 'Scenarier'))
            p.add_widget(sub_bar)

            self.lyd_area = BoxLayout()
            p.add_widget(self.lyd_area)

            self._lyd_render_sub()
            return p

        def _lyd_switch(self, which):
            """Bytt mellom sub-faner under Lyd."""
            self._lyd_sub = which
            self._lyd_render_sub()

        def _lyd_render_sub(self):
            """Rendre riktig sub-visning inne i lyd_area."""
            self.lyd_area.clear_widgets()
            if self._lyd_sub == 'mus':
                self.lyd_area.add_widget(self._mk_mus())
            elif self._lyd_sub == 'amb':
                self.lyd_area.add_widget(self._mk_amb())
            elif self._lyd_sub == 'one':
                self.lyd_area.add_widget(self._mk_oneshot())
            else:
                self.lyd_area.add_widget(self._mk_scn())

        # ---------- ONE-SHOT ----------
        def _mk_oneshot(self):
            """Liste over lokale one-shot-lyder. Tap = avspill."""
            p = BoxLayout(orientation='vertical', spacing=dp(6))

            hdr = mklbl("Trykk for å spille av", color=DIM, size=11, h=22)
            p.add_widget(hdr)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(6),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            try:
                if not os.path.exists(ONESHOT_DIR):
                    g.add_widget(mklbl("One-shot-mappen finnes ikke ennå.\n"
                                       "Start appen på nytt.",
                                       color=DIM, size=11, wrap=True))
                else:
                    fl = sorted([f for f in os.listdir(ONESHOT_DIR)
                                 if f.lower().endswith(SND_EXT)])
                    if not fl:
                        g.add_widget(mklbl(
                            "Ingen one-shot-lyder funnet.\n\n"
                            "Legg korte lydeffekter (sword clash,\n"
                            "thunder crack, door slam, osv.) i:\n"
                            f"{ONESHOT_DIR}\n\n"
                            "Støttede formater:\n"
                            ".mp3 .ogg .wav .flac .m4a .aac",
                            color=DIM, size=11, wrap=True))
                    else:
                        hdr.text = f"{len(fl)} lyder – trykk for å spille av"
                        for fn in fl:
                            full = os.path.join(ONESHOT_DIR, fn)
                            g.add_widget(
                                mkbtn(fn,
                                      lambda fp=full: self.oneshot.fire(fp),
                                      small=True, size_hint_y=None,
                                      height=dp(42)))
            except Exception as e:
                log(f"oneshot list: {e}")
                g.add_widget(mklbl(f"Feil: {e}", color=RED, size=11))

            scroll.add_widget(g)
            p.add_widget(scroll)
            p.add_widget(mkvol(self.oneshot.vol, 0.8))
            p.add_widget(mkbtn("Stopp alle one-shots",
                               self.oneshot.stop_all,
                               danger=True,
                               size_hint_y=None, height=dp(40)))
            return p

        # ---------- SCENARIER ----------
        def _mk_scn(self):
            """Hoved-scenario-fane: ruter til riktig visning."""
            if self._scn_view == 'editor':
                return self._mk_scn_editor()
            elif self._scn_view == 'scenes':
                return self._mk_scn_scenes()
            return self._mk_scn_list()

        def _mk_scn_list(self):
            """Liste over lagrede scenarioer + Nytt-knapp."""
            p = BoxLayout(orientation='vertical', spacing=dp(6))

            top = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            top.add_widget(mkbtn("+ Nytt scenario", self._scn_new,
                                 accent=True))
            p.add_widget(top)

            p.add_widget(mklbl("Hvert scenario inneholder scener.\n"
                               "Hver scene har lyd-bokser (lag) og one-shots.",
                               color=DIM, size=10, wrap=True))

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(6),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            if not self.scenarios:
                g.add_widget(mklbl("Ingen scenarioer ennå.\n"
                                   "Trykk + for å lage ett.",
                                   color=DIM, size=11, wrap=True))
            else:
                for i, sc in enumerate(self.scenarios):
                    row = BoxLayout(size_hint_y=None, height=dp(48),
                                    spacing=dp(4))
                    name = sc.get('name', f'Scenario {i+1}')
                    n_scenes = len(sc.get('scenes', []))
                    row.add_widget(mkbtn(
                        f"{name}  ({n_scenes} scener)",
                        lambda idx=i: self._scn_open(idx)))
                    row.add_widget(mkbtn("Endre", lambda idx=i:
                                         self._scn_rename(idx),
                                         small=True,
                                         size_hint_x=None, width=dp(64)))
                    row.add_widget(mkbtn("X", lambda idx=i:
                                         self._scn_delete(idx),
                                         danger=True, small=True,
                                         size_hint_x=None, width=dp(40)))
                    g.add_widget(row)

            scroll.add_widget(g)
            p.add_widget(scroll)
            return p

        def _scn_refresh(self):
            """Re-render gjeldende scenario-visning."""
            if self._lyd_sub == 'scn':
                self._lyd_render_sub()

        def _scn_new(self):
            """Opprett nytt scenario med Vogler-stadier."""
            def _create(name):
                if not name:
                    name = f"Scenario {len(self.scenarios)+1}"
                scenes = []
                for stage in VOGLER_STAGES:
                    scenes.append({
                        'name': stage,
                        'loop_boxes': [
                            {'label': f'Lag {j+1}', 'kind': None,
                             'src': None, 'volume': 0.7}
                            for j in range(6)
                        ],
                        'oneshot_boxes': [
                            {'label': f'SFX {j+1}', 'src': None,
                             'volume': 0.8}
                            for j in range(4)
                        ],
                    })
                self.scenarios.append({'name': name, 'scenes': scenes})
                save_json(SCENARIO_FILE, self.scenarios)
                self._scn_refresh()
            self._txt_popup("Nytt scenario", "Navn:", "", _create)

        def _scn_rename(self, idx):
            sc = self.scenarios[idx]
            def _save(new_name):
                if new_name:
                    sc['name'] = new_name
                    save_json(SCENARIO_FILE, self.scenarios)
                    self._scn_refresh()
            self._txt_popup("Endre scenarionavn", "Navn:",
                            sc.get('name', ''), _save)

        def _scn_delete(self, idx):
            sc = self.scenarios[idx]
            def _yes():
                self._scn_stop_all()
                self.scenarios.pop(idx)
                save_json(SCENARIO_FILE, self.scenarios)
                self._scn_refresh()
            self._confirm(f"Slett scenario '{sc.get('name','?')}'?", _yes)

        def _scn_open(self, idx):
            self._scn_stop_all()
            self._scn_idx = idx
            self._scn_view = 'scenes'
            self._scn_refresh()

        def _scn_back_to_list(self):
            self._scn_stop_all()
            self._scn_idx = None
            self._scn_view = 'list'
            self._scn_refresh()

        def _mk_scn_scenes(self):
            """Liste over scener i valgt scenario, med rekkefølge-knapper."""
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            sc = self.scenarios[self._scn_idx]

            top = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            top.add_widget(mkbtn("< Scenarier", self._scn_back_to_list,
                                 small=True, size_hint_x=None, width=dp(110)))
            top.add_widget(mklbl(sc.get('name', '?'),
                                 color=GOLD, size=14, bold=True))
            p.add_widget(top)

            top2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            top2.add_widget(mkbtn("+ Legg til scene",
                                  lambda: self._scn_add_scene(),
                                  accent=True))
            p.add_widget(top2)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(6),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            scenes = sc.get('scenes', [])
            if not scenes:
                g.add_widget(mklbl("Ingen scener. Trykk + for å legge til.",
                                   color=DIM, size=11, wrap=True))
            else:
                for i, sn in enumerate(scenes):
                    row = BoxLayout(size_hint_y=None, height=dp(48),
                                    spacing=dp(2))
                    label = f"{i+1}. {sn.get('name','?')}"
                    row.add_widget(mkbtn(label,
                        lambda idx=i: self._scn_open_scene(idx)))
                    row.add_widget(mkbtn("^",
                        lambda idx=i: self._scn_move_scene(idx, -1),
                        small=True, size_hint_x=None, width=dp(34)))
                    row.add_widget(mkbtn("v",
                        lambda idx=i: self._scn_move_scene(idx, 1),
                        small=True, size_hint_x=None, width=dp(34)))
                    row.add_widget(mkbtn("Endre",
                        lambda idx=i: self._scn_rename_scene(idx),
                        small=True, size_hint_x=None, width=dp(60)))
                    row.add_widget(mkbtn("X",
                        lambda idx=i: self._scn_delete_scene(idx),
                        danger=True, small=True,
                        size_hint_x=None, width=dp(36)))
                    g.add_widget(row)

            scroll.add_widget(g)
            p.add_widget(scroll)
            return p

        def _scn_add_scene(self):
            sc = self.scenarios[self._scn_idx]
            def _create(name):
                if not name:
                    name = f"Scene {len(sc['scenes'])+1}"
                sc['scenes'].append({
                    'name': name,
                    'loop_boxes': [
                        {'label': f'Lag {j+1}', 'kind': None,
                         'src': None, 'volume': 0.7}
                        for j in range(6)
                    ],
                    'oneshot_boxes': [
                        {'label': f'SFX {j+1}', 'src': None,
                         'volume': 0.8}
                        for j in range(4)
                    ],
                })
                save_json(SCENARIO_FILE, self.scenarios)
                self._scn_refresh()
            self._txt_popup("Ny scene", "Scenenavn:", "", _create)

        def _scn_rename_scene(self, scene_idx):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][scene_idx]
            def _save(new_name):
                if new_name:
                    sn['name'] = new_name
                    save_json(SCENARIO_FILE, self.scenarios)
                    self._scn_refresh()
            self._txt_popup("Endre scenenavn", "Navn:",
                            sn.get('name', ''), _save)

        def _scn_delete_scene(self, scene_idx):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][scene_idx]
            def _yes():
                sc['scenes'].pop(scene_idx)
                save_json(SCENARIO_FILE, self.scenarios)
                self._scn_refresh()
            self._confirm(f"Slett scene '{sn.get('name','?')}'?", _yes)

        def _scn_move_scene(self, scene_idx, delta):
            sc = self.scenarios[self._scn_idx]
            scenes = sc['scenes']
            new_idx = scene_idx + delta
            if 0 <= new_idx < len(scenes):
                scenes[scene_idx], scenes[new_idx] = scenes[new_idx], scenes[scene_idx]
                save_json(SCENARIO_FILE, self.scenarios)
                self._scn_refresh()

        def _scn_open_scene(self, scene_idx):
            self._scn_stop_all()
            self._scn_scene_idx = scene_idx
            self._scn_view = 'editor'
            self._scn_refresh()

        def _scn_back_to_scenes(self):
            self._scn_stop_all()
            self._scn_scene_idx = None
            self._scn_view = 'scenes'
            self._scn_refresh()

        def _mk_scn_editor(self):
            """Scene-editor: loop-bokser i grid + one-shot-rad."""
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            self._scn_box_widgets = []

            # Header
            top = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            top.add_widget(mkbtn("< Scener", self._scn_back_to_scenes,
                                 small=True, size_hint_x=None, width=dp(90)))
            top.add_widget(mklbl(sn.get('name', '?'),
                                 color=GOLD, size=13, bold=True))
            p.add_widget(top)

            # Loop-bokser overskrift + +/- knapper
            loop_hdr = BoxLayout(size_hint_y=None, height=dp(34),
                                 spacing=dp(4))
            loop_hdr.add_widget(mklbl("Lag (loop)", color=GDIM, size=11,
                                      bold=True))
            loop_hdr.add_widget(mkbtn("+ Boks",
                lambda: self._scn_add_box('loop'),
                small=True, size_hint_x=None, width=dp(80)))
            loop_hdr.add_widget(mkbtn("- Boks",
                lambda: self._scn_remove_box('loop'),
                danger=True, small=True,
                size_hint_x=None, width=dp(80)))
            p.add_widget(loop_hdr)

            # Loop-grid (2 kolonner)
            loop_scroll = ScrollView(size_hint_y=0.55)
            loop_grid = GridLayout(cols=2, spacing=dp(6), padding=dp(4),
                                   size_hint_y=None)
            loop_grid.bind(minimum_height=loop_grid.setter('height'))
            for i, box in enumerate(sn.get('loop_boxes', [])):
                w = self._mk_loop_box_face(i, box)
                loop_grid.add_widget(w)
            loop_scroll.add_widget(loop_grid)
            p.add_widget(loop_scroll)

            # One-shot overskrift + +/-
            os_hdr = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(4))
            os_hdr.add_widget(mklbl("One-shots", color=GDIM, size=11,
                                    bold=True))
            os_hdr.add_widget(mkbtn("+",
                lambda: self._scn_add_box('one'),
                small=True, size_hint_x=None, width=dp(50)))
            os_hdr.add_widget(mkbtn("-",
                lambda: self._scn_remove_box('one'),
                danger=True, small=True,
                size_hint_x=None, width=dp(50)))
            p.add_widget(os_hdr)

            # One-shot-rad (horisontal scroll)
            os_scroll = ScrollView(size_hint_y=None, height=dp(76),
                                   do_scroll_x=True, do_scroll_y=False)
            os_row = BoxLayout(orientation='horizontal',
                               size_hint_x=None,
                               spacing=dp(6), padding=dp(4))
            os_row.bind(minimum_width=os_row.setter('width'))
            for i, box in enumerate(sn.get('oneshot_boxes', [])):
                w = self._mk_oneshot_box_face(i, box)
                os_row.add_widget(w)
            os_scroll.add_widget(os_row)
            p.add_widget(os_scroll)

            # Footer-kontroller
            foot = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            foot.add_widget(mkbtn("Spill alle lag",
                self._scn_play_all_loops, accent=True))
            foot.add_widget(mkbtn("Stopp alle",
                self._scn_stop_all, danger=True))
            p.add_widget(foot)

            return p

        def _mk_loop_box_face(self, idx, box):
            """Liten boks for et loop-lag i scene-editoren."""
            kind = box.get('kind')
            src = box.get('src')
            label = box.get('label', f'Lag {idx+1}')
            playing = self._scn_box_is_playing(idx)
            bg = LOOP_BG_ON if playing else LOOP_BG
            sub_hint = '— tom —'
            if kind == 'music' and src:
                sub_hint = os.path.basename(src)
            elif kind == 'ambient' and src:
                sub_hint = src  # navnet er src
            elif kind == 'local' and src:
                sub_hint = os.path.basename(src)

            outer = RBox(orientation='vertical',
                         size_hint_y=None, height=dp(96),
                         padding=dp(6), spacing=dp(2),
                         bg_color=bg, radius=dp(12))
            # Trykk på label-rad for å åpne editor
            inner = BoxLayout(orientation='vertical', spacing=dp(2))

            top_lbl = Label(text=label, color=GOLD, font_size=sp(11),
                            bold=True, size_hint_y=None, height=dp(20),
                            halign='center')
            top_lbl.bind(size=top_lbl.setter('text_size'))
            inner.add_widget(top_lbl)

            sub_lbl = Label(text=sub_hint,
                            color=TXT if src else DIM,
                            font_size=sp(9),
                            size_hint_y=None, height=dp(18),
                            halign='center', shorten=True)
            sub_lbl.bind(size=sub_lbl.setter('text_size'))
            inner.add_widget(sub_lbl)

            # Kontrollrad
            ctrl = BoxLayout(size_hint_y=None, height=dp(34),
                             spacing=dp(3))
            play_txt = "Stopp" if playing else "Spill"
            play_btn = mkbtn(play_txt,
                lambda i=idx: self._scn_toggle_layer(i),
                small=True, accent=playing)
            ctrl.add_widget(play_btn)
            edit_btn = mkbtn("Endre",
                lambda i=idx: self._scn_edit_loop_box(i),
                small=True)
            ctrl.add_widget(edit_btn)
            inner.add_widget(ctrl)

            outer.add_widget(inner)
            return outer

        def _mk_oneshot_box_face(self, idx, box):
            """Liten boks for en one-shot, mørkere farge med gull-ramme."""
            label = box.get('label', f'SFX {idx+1}')
            src = box.get('src')

            # Wrapper gir gull-ramme via FramedBox
            wrap = FramedBox(orientation='vertical',
                             size_hint_x=None, width=dp(90),
                             padding=dp(2), frame_color=ONE_BORDER)
            inner = RBox(orientation='vertical',
                         padding=dp(4), spacing=dp(2),
                         bg_color=ONE_BG, radius=dp(8))
            # Stor "fyr-av"-knapp
            fire = mkbtn(label,
                lambda i=idx: self._scn_fire_oneshot(i),
                small=True, accent=True, size_hint_y=0.65)
            inner.add_widget(fire)
            edit = mkbtn("Endre",
                lambda i=idx: self._scn_edit_oneshot_box(i),
                small=True, size_hint_y=0.35)
            inner.add_widget(edit)
            wrap.add_widget(inner)
            return wrap

        # ----- Scene-handlinger -----
        def _scn_add_box(self, kind):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            if kind == 'loop':
                arr = sn.setdefault('loop_boxes', [])
                arr.append({'label': f'Lag {len(arr)+1}', 'kind': None,
                            'src': None, 'volume': 0.7})
            else:
                arr = sn.setdefault('oneshot_boxes', [])
                arr.append({'label': f'SFX {len(arr)+1}', 'src': None,
                            'volume': 0.8})
            save_json(SCENARIO_FILE, self.scenarios)
            self._scn_refresh()

        def _scn_remove_box(self, kind):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            arr = sn.get('loop_boxes' if kind == 'loop' else 'oneshot_boxes',
                         [])
            if not arr:
                return
            # Stopp evt. avspilling fra siste boks før vi fjerner den
            if kind == 'loop':
                last_idx = len(arr) - 1
                self._scn_stop_layer(last_idx)
            arr.pop()
            save_json(SCENARIO_FILE, self.scenarios)
            self._scn_refresh()

        def _scn_box_is_playing(self, idx):
            if idx >= len(self._scn_layers):
                return False
            lp = self._scn_layers[idx]
            return lp is not None and lp.is_playing

        def _scn_ensure_layers_size(self, n):
            """Sørg for at _scn_layers har plass til n bokser."""
            while len(self._scn_layers) < n:
                self._scn_layers.append(None)

        def _scn_toggle_layer(self, idx):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            box = sn['loop_boxes'][idx]
            self._scn_ensure_layers_size(len(sn['loop_boxes']))
            lp = self._scn_layers[idx]
            if lp and lp.is_playing:
                lp.stop()
                self._scn_layers[idx] = None
            else:
                if not box.get('src') or not box.get('kind'):
                    self._toast("Boksen har ingen lyd. Trykk 'Endre'.")
                    return
                lp = LayerPlayer()
                lp._v = box.get('volume', 0.7)
                src = box['src']
                kind = box['kind']
                if kind == 'music':
                    lp.play(src, is_url=False, loop=True)
                elif kind == 'ambient':
                    # src for ambient er URL
                    lp.play(src, is_url=True, loop=True)
                elif kind == 'local':
                    lp.play(src, is_url=False, loop=True)
                self._scn_layers[idx] = lp
            self._scn_refresh()

        def _scn_stop_layer(self, idx):
            if idx < len(self._scn_layers):
                lp = self._scn_layers[idx]
                if lp:
                    lp.stop()
                    self._scn_layers[idx] = None

        def _scn_play_all_loops(self):
            """Start alle lag som har en lyd konfigurert."""
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            self._scn_ensure_layers_size(len(sn['loop_boxes']))
            for i, box in enumerate(sn['loop_boxes']):
                if not box.get('src') or not box.get('kind'):
                    continue
                lp = self._scn_layers[i]
                if lp and lp.is_playing:
                    continue
                lp = LayerPlayer()
                lp._v = box.get('volume', 0.7)
                if box['kind'] == 'ambient':
                    lp.play(box['src'], is_url=True, loop=True)
                else:
                    lp.play(box['src'], is_url=False, loop=True)
                self._scn_layers[i] = lp
            self._scn_refresh()

        def _scn_stop_all(self):
            """Stopp alle aktive lag-spillere."""
            for lp in self._scn_layers:
                if lp:
                    try: lp.stop()
                    except: pass
            self._scn_layers = []
            if hasattr(self, '_lyd_sub') and self._lyd_sub == 'scn' \
                    and self._scn_view == 'editor':
                self._scn_refresh()

        def _scn_fire_oneshot(self, idx):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            box = sn['oneshot_boxes'][idx]
            src = box.get('src')
            if not src:
                self._toast("One-shot er tom. Trykk 'Endre'.")
                return
            old_v = self.oneshot._v
            self.oneshot._v = box.get('volume', 0.8)
            self.oneshot.fire(src)
            self.oneshot._v = old_v

        # ----- Box-editorer (overlay) -----
        def _scn_edit_loop_box(self, idx):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            box = sn['loop_boxes'][idx]
            self._show_loop_editor(idx, box)

        def _scn_edit_oneshot_box(self, idx):
            sc = self.scenarios[self._scn_idx]
            sn = sc['scenes'][self._scn_scene_idx]
            box = sn['oneshot_boxes'][idx]
            self._show_oneshot_editor(idx, box)

        # ----- Overlay-bygger (felles) -----
        def _root_float(self):
            """Finn FloatLayout-roten for å plassere overlays."""
            r = self.root
            if isinstance(r, FloatLayout):
                return r
            # Walk up
            w = r
            while w and not isinstance(w, FloatLayout):
                w = w.parent
            return w

        def _open_overlay(self, content_box):
            """Vis et overlay sentrert på toppen av appen."""
            self._close_overlay()
            fl = self._root_float()
            if fl is None:
                return
            # Dim
            from kivy.graphics import Color as GC, Rectangle as GR
            dim = Widget(size_hint=(1, 1))
            with dim.canvas:
                GC(rgba=[0, 0, 0, 0.65])
                dr = GR(pos=dim.pos, size=dim.size)
            dim.bind(pos=lambda w, v: setattr(dr, 'pos', w.pos),
                     size=lambda w, v: setattr(dr, 'size', w.size))
            # Tap på dim lukker
            dim.bind(on_touch_down=lambda w, t: self._close_overlay() or True)
            self._scn_overlay_dim = dim
            self._scn_overlay = content_box
            fl.add_widget(dim)
            fl.add_widget(content_box)

        def _close_overlay(self):
            fl = self._root_float()
            for attr in ('_scn_overlay', '_scn_overlay_dim'):
                w = getattr(self, attr, None)
                if w and w.parent:
                    try: w.parent.remove_widget(w)
                    except: pass
                setattr(self, attr, None)

        def _txt_popup(self, title, prompt, init_val, on_ok):
            """Enkel tekst-input-popup."""
            box = RBox(orientation='vertical',
                       size_hint=(0.85, None), height=dp(220),
                       pos_hint={'center_x': 0.5, 'center_y': 0.5},
                       padding=dp(12), spacing=dp(8),
                       bg_color=BG, radius=dp(14))
            box.add_widget(mklbl(title, color=GOLD, size=14, bold=True,
                                 h=28))
            box.add_widget(mklbl(prompt, color=DIM, size=11, h=20))
            ti = TextInput(text=init_val, multiline=False,
                           size_hint_y=None, height=dp(40),
                           background_color=INPUT,
                           foreground_color=TXT, cursor_color=GOLD,
                           font_size=sp(13))
            box.add_widget(ti)
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            def _ok():
                v = ti.text.strip()
                self._close_overlay()
                on_ok(v)
            row.add_widget(mkbtn("Avbryt", self._close_overlay,
                                 small=True))
            row.add_widget(mkbtn("OK", _ok, accent=True))
            box.add_widget(row)
            self._open_overlay(box)
            # Fokus etter en frame
            Clock.schedule_once(lambda dt: setattr(ti, 'focus', True), 0.1)

        def _confirm(self, question, on_yes):
            """Ja/Nei-bekreftelsespopup."""
            box = RBox(orientation='vertical',
                       size_hint=(0.85, None), height=dp(180),
                       pos_hint={'center_x': 0.5, 'center_y': 0.5},
                       padding=dp(12), spacing=dp(10),
                       bg_color=BG, radius=dp(14))
            q = mklbl(question, color=TXT, size=12, wrap=True)
            box.add_widget(q)
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            row.add_widget(mkbtn("Nei", self._close_overlay, small=True))
            def _yes():
                self._close_overlay()
                on_yes()
            row.add_widget(mkbtn("Ja", _yes, danger=True))
            box.add_widget(row)
            self._open_overlay(box)

        def _toast(self, msg):
            """Kort beskjed nederst på skjermen."""
            fl = self._root_float()
            if fl is None:
                return
            t = RBox(orientation='vertical',
                     size_hint=(None, None), size=(dp(280), dp(48)),
                     pos_hint={'center_x': 0.5, 'y': 0.10},
                     padding=dp(10), bg_color=BG, radius=dp(12))
            l = Label(text=msg, color=GOLD, font_size=sp(11), bold=True,
                      halign='center')
            l.bind(size=l.setter('text_size'))
            t.add_widget(l)
            fl.add_widget(t)
            def _rm(dt):
                if t.parent:
                    try: t.parent.remove_widget(t)
                    except: pass
            Clock.schedule_once(_rm, 1.8)

        # ----- Loop-boks editor -----
        def _show_loop_editor(self, box_idx, box):
            """Overlay for å konfigurere et loop-lag."""
            # Lokal state for editoren
            state = {
                'kind': box.get('kind'),
                'src': box.get('src'),
                'sub_kind': box.get('kind') or 'music',  # aktiv source-fane
                'volume': box.get('volume', 0.7),
                'label': box.get('label', f'Lag {box_idx+1}'),
                'preview': None,  # LayerPlayer for forhåndsvisning
            }

            outer = RBox(orientation='vertical',
                         size_hint=(0.95, 0.92),
                         pos_hint={'center_x': 0.5, 'center_y': 0.5},
                         padding=dp(10), spacing=dp(6),
                         bg_color=BG, radius=dp(14))

            # Header
            outer.add_widget(mklbl(f"Endre lag {box_idx+1}",
                                   color=GOLD, size=14, bold=True, h=26))

            # Navnefelt
            outer.add_widget(mklbl("Navn:", color=DIM, size=11, h=18))
            name_in = TextInput(text=state['label'], multiline=False,
                                size_hint_y=None, height=dp(38),
                                background_color=INPUT, foreground_color=TXT,
                                cursor_color=GOLD, font_size=sp(12))
            outer.add_widget(name_in)

            # Source-kind-velger
            kind_row = BoxLayout(size_hint_y=None, height=dp(38),
                                 spacing=dp(4))
            buttons = {}
            def _set_kind(k):
                state['sub_kind'] = k
                for kk, btn in buttons.items():
                    btn.state = 'down' if kk == k else 'normal'
                    btn.bg_color = BTNH if kk == k else BTN
                    btn.color = GOLD if kk == k else DIM
                _refresh_list()

            for k, lab in [('music', 'Musikk'), ('ambient', 'Ambient'),
                           ('local', 'Egne')]:
                act = state['sub_kind'] == k
                b = RToggle(text=lab, group='loop_kind',
                            state='down' if act else 'normal',
                            bg_color=BTNH if act else BTN,
                            color=GOLD if act else DIM,
                            font_size=sp(11), bold=True)
                b.bind(on_release=lambda btn, kk=k: _set_kind(kk))
                buttons[k] = b
                kind_row.add_widget(b)
            outer.add_widget(kind_row)

            # Valgt-indikator
            sel_lbl = mklbl("Valgt: " + (
                f"{state['kind']} – {os.path.basename(state['src']) if state['src'] else '?'}"
                if state['src'] else "(ingen)"
            ), color=DIM, size=10, h=20, wrap=True)
            outer.add_widget(sel_lbl)

            # Liste
            list_scroll = ScrollView(size_hint_y=1)
            list_grid = GridLayout(cols=1, spacing=dp(3), padding=dp(4),
                                   size_hint_y=None)
            list_grid.bind(minimum_height=list_grid.setter('height'))
            list_scroll.add_widget(list_grid)
            outer.add_widget(list_scroll)

            def _select(kind, src, display):
                state['kind'] = kind
                state['src'] = src
                sel_lbl.text = f"Valgt: {display}"
                sel_lbl.color = GOLD

            def _refresh_list():
                list_grid.clear_widgets()
                k = state['sub_kind']
                if k == 'music':
                    if not os.path.exists(MUSIC_DIR):
                        list_grid.add_widget(mklbl("Mappe ikke funnet",
                                                   color=DIM, size=11,
                                                   h=24))
                        return
                    fl = sorted([f for f in os.listdir(MUSIC_DIR)
                                 if f.lower().endswith(SND_EXT)])
                    if not fl:
                        list_grid.add_widget(mklbl("Ingen filer i musikk/",
                                                   color=DIM, size=11,
                                                   h=24))
                    for fn in fl:
                        full = os.path.join(MUSIC_DIR, fn)
                        list_grid.add_widget(
                            mkbtn(fn,
                                  lambda fp=full, n=fn:
                                      _select('music', fp, n),
                                  small=True, size_hint_y=None,
                                  height=dp(38)))
                elif k == 'ambient':
                    for snd in AMBIENT_SOUNDS:
                        if 'url' not in snd:
                            list_grid.add_widget(
                                mklbl(snd['name'], color=GDIM, size=10,
                                      bold=True, h=22))
                        else:
                            list_grid.add_widget(
                                mkbtn(snd['name'],
                                      lambda u=snd['url'], n=snd['name']:
                                          _select('ambient', u, n),
                                      small=True, size_hint_y=None,
                                      height=dp(38)))
                else:  # local
                    if not os.path.exists(ONESHOT_DIR):
                        list_grid.add_widget(mklbl("Mappe ikke funnet",
                                                   color=DIM, size=11,
                                                   h=24))
                        return
                    fl = sorted([f for f in os.listdir(ONESHOT_DIR)
                                 if f.lower().endswith(SND_EXT)])
                    if not fl:
                        list_grid.add_widget(mklbl(
                            f"Ingen filer i oneshots/.\nLegg egne lyder der.",
                            color=DIM, size=11, h=44, wrap=True))
                    for fn in fl:
                        full = os.path.join(ONESHOT_DIR, fn)
                        list_grid.add_widget(
                            mkbtn(fn,
                                  lambda fp=full, n=fn:
                                      _select('local', fp, n),
                                  small=True, size_hint_y=None,
                                  height=dp(38)))

            _refresh_list()

            # Volum
            outer.add_widget(mklbl("Volum:", color=DIM, size=11, h=18))
            vol_row = BoxLayout(size_hint_y=None, height=dp(36))
            vol_sl = Slider(min=0, max=1, value=state['volume'])
            def _vol_change(s, v):
                state['volume'] = v
                if state['preview']:
                    state['preview'].vol(v)
            vol_sl.bind(value=_vol_change)
            vol_row.add_widget(vol_sl)
            outer.add_widget(vol_row)

            # Knapper
            row1 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
            def _preview():
                if state['preview']:
                    state['preview'].stop()
                    state['preview'] = None
                    prev_btn.text = "Forhåndsvis"
                    return
                if not state['src'] or not state['kind']:
                    self._toast("Velg en lyd først")
                    return
                lp = LayerPlayer()
                lp._v = state['volume']
                if state['kind'] == 'ambient':
                    lp.play(state['src'], is_url=True, loop=True)
                else:
                    lp.play(state['src'], is_url=False, loop=True)
                state['preview'] = lp
                prev_btn.text = "Stopp"
            prev_btn = mkbtn("Forhåndsvis", _preview, small=True)
            row1.add_widget(prev_btn)

            def _clear():
                state['kind'] = None
                state['src'] = None
                sel_lbl.text = "Valgt: (ingen)"
                sel_lbl.color = DIM
            row1.add_widget(mkbtn("Fjern lyd", _clear, danger=True,
                                  small=True))
            outer.add_widget(row1)

            row2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            def _close_local():
                if state['preview']:
                    try: state['preview'].stop()
                    except: pass
                    state['preview'] = None
                self._close_overlay()
            row2.add_widget(mkbtn("Avbryt", _close_local, small=True))

            def _save():
                # Stopp evt. forhåndsvisning
                if state['preview']:
                    try: state['preview'].stop()
                    except: pass
                    state['preview'] = None
                # Stopp aktiv layer hvis vi endret kilden
                old_src = box.get('src')
                box['label'] = name_in.text.strip() or f'Lag {box_idx+1}'
                box['kind'] = state['kind']
                box['src'] = state['src']
                box['volume'] = state['volume']
                if old_src != state['src']:
                    self._scn_stop_layer(box_idx)
                else:
                    # Oppdater volum hvis lag spiller
                    if box_idx < len(self._scn_layers):
                        lp = self._scn_layers[box_idx]
                        if lp:
                            lp.vol(state['volume'])
                save_json(SCENARIO_FILE, self.scenarios)
                self._close_overlay()
                self._scn_refresh()
            row2.add_widget(mkbtn("Lagre", _save, accent=True))
            outer.add_widget(row2)

            self._open_overlay(outer)

        # ----- One-shot-boks editor -----
        def _show_oneshot_editor(self, box_idx, box):
            """Overlay for å konfigurere en one-shot."""
            state = {
                'src': box.get('src'),
                'volume': box.get('volume', 0.8),
                'label': box.get('label', f'SFX {box_idx+1}'),
            }

            outer = RBox(orientation='vertical',
                         size_hint=(0.95, 0.85),
                         pos_hint={'center_x': 0.5, 'center_y': 0.5},
                         padding=dp(10), spacing=dp(6),
                         bg_color=BG, radius=dp(14))

            outer.add_widget(mklbl(f"Endre one-shot {box_idx+1}",
                                   color=GOLD, size=14, bold=True, h=26))

            outer.add_widget(mklbl("Navn:", color=DIM, size=11, h=18))
            name_in = TextInput(text=state['label'], multiline=False,
                                size_hint_y=None, height=dp(38),
                                background_color=INPUT, foreground_color=TXT,
                                cursor_color=GOLD, font_size=sp(12))
            outer.add_widget(name_in)

            sel_lbl = mklbl("Valgt: " + (
                os.path.basename(state['src']) if state['src'] else "(ingen)"
            ), color=GOLD if state['src'] else DIM,
                            size=10, h=20, wrap=True)
            outer.add_widget(sel_lbl)

            outer.add_widget(mklbl(
                f"Velg lyd fra oneshots/-mappa:",
                color=DIM, size=11, h=20))

            list_scroll = ScrollView(size_hint_y=1)
            list_grid = GridLayout(cols=1, spacing=dp(3), padding=dp(4),
                                   size_hint_y=None)
            list_grid.bind(minimum_height=list_grid.setter('height'))

            try:
                if not os.path.exists(ONESHOT_DIR):
                    list_grid.add_widget(mklbl("Mappe ikke funnet",
                                               color=DIM, size=11, h=24))
                else:
                    fl = sorted([f for f in os.listdir(ONESHOT_DIR)
                                 if f.lower().endswith(SND_EXT)])
                    if not fl:
                        list_grid.add_widget(mklbl(
                            f"Ingen filer.\nLegg lyder i:\n{ONESHOT_DIR}",
                            color=DIM, size=11, h=60, wrap=True))
                    for fn in fl:
                        full = os.path.join(ONESHOT_DIR, fn)
                        def _sel(fp=full, n=fn):
                            state['src'] = fp
                            sel_lbl.text = f"Valgt: {n}"
                            sel_lbl.color = GOLD
                        list_grid.add_widget(
                            mkbtn(fn, _sel, small=True,
                                  size_hint_y=None, height=dp(38)))
            except Exception as e:
                list_grid.add_widget(mklbl(f"Feil: {e}",
                                           color=RED, size=11, h=24))
            list_scroll.add_widget(list_grid)
            outer.add_widget(list_scroll)

            outer.add_widget(mklbl("Volum:", color=DIM, size=11, h=18))
            vol_row = BoxLayout(size_hint_y=None, height=dp(36))
            vol_sl = Slider(min=0, max=1, value=state['volume'])
            vol_sl.bind(value=lambda s, v: state.update({'volume': v}))
            vol_row.add_widget(vol_sl)
            outer.add_widget(vol_row)

            row1 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
            def _test():
                if not state['src']:
                    self._toast("Velg en lyd først")
                    return
                old_v = self.oneshot._v
                self.oneshot._v = state['volume']
                self.oneshot.fire(state['src'])
                self.oneshot._v = old_v
            row1.add_widget(mkbtn("Test", _test, accent=True, small=True))
            def _clear():
                state['src'] = None
                sel_lbl.text = "Valgt: (ingen)"
                sel_lbl.color = DIM
            row1.add_widget(mkbtn("Fjern lyd", _clear, danger=True,
                                  small=True))
            outer.add_widget(row1)

            row2 = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            row2.add_widget(mkbtn("Avbryt", self._close_overlay, small=True))
            def _save():
                box['label'] = name_in.text.strip() or f'SFX {box_idx+1}'
                box['src'] = state['src']
                box['volume'] = state['volume']
                save_json(SCENARIO_FILE, self.scenarios)
                self._close_overlay()
                self._scn_refresh()
            row2.add_widget(mkbtn("Lagre", _save, accent=True))
            outer.add_widget(row2)

            self._open_overlay(outer)


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
            """Karakter-fane med sub-tabs: Karakterer og Initiativ."""
            self._init_tracker_init()
            # Standard: vis karakter-lista
            if not hasattr(self, '_tool_sub'):
                self._tool_sub = 'chars'

            p = BoxLayout(orientation='vertical', spacing=dp(6))

            # Sub-tab-rad
            sub_bar = RBox(size_hint_y=None, height=dp(42),
                           spacing=dp(4), padding=[dp(6), dp(4)],
                           bg_color=BTN, radius=dp(10))
            b_chars = RToggle(
                text='Karakterer', group='tool_sub',
                state='down' if self._tool_sub == 'chars' else 'normal',
                bg_color=BTNH if self._tool_sub == 'chars' else BTN,
                color=GOLD if self._tool_sub == 'chars' else DIM,
                font_size=sp(11), bold=True)
            b_chars.bind(on_release=lambda b: self._tool_switch('chars'))
            sub_bar.add_widget(b_chars)

            b_init = RToggle(
                text='Initiativ', group='tool_sub',
                state='down' if self._tool_sub == 'init' else 'normal',
                bg_color=BTNH if self._tool_sub == 'init' else BTN,
                color=GOLD if self._tool_sub == 'init' else DIM,
                font_size=sp(11), bold=True)
            b_init.bind(on_release=lambda b: self._tool_switch('init'))
            sub_bar.add_widget(b_init)

            b_map = RToggle(
                text='Kart', group='tool_sub',
                state='down' if self._tool_sub == 'map' else 'normal',
                bg_color=BTNH if self._tool_sub == 'map' else BTN,
                color=GOLD if self._tool_sub == 'map' else DIM,
                font_size=sp(11), bold=True)
            b_map.bind(on_release=lambda b: self._tool_switch('map'))
            sub_bar.add_widget(b_map)
            p.add_widget(sub_bar)

            # Handlings-rad (kun for karakter-lista)
            self._tool_action_bar = BoxLayout(
                size_hint_y=None, height=dp(42),
                spacing=dp(6), padding=[dp(6), 0])
            p.add_widget(self._tool_action_bar)

            self.tool_area = BoxLayout()
            p.add_widget(self.tool_area)

            self._tool_render_sub()
            return p

        def _tool_switch(self, which):
            """Bytt mellom karakterer og initiativ."""
            self._tool_sub = which
            self._tool_render_sub()

        def _tool_render_sub(self):
            """Rendre riktig sub-visning."""
            # Oppdater handlings-rad
            self._tool_action_bar.clear_widgets()
            if self._tool_sub == 'chars':
                self._tool_action_bar.add_widget(
                    mkbtn("+ Ny", self._new_char, accent=True,
                          size_hint_x=0.35))
                self._tool_action_bar.add_widget(
                    mkbtn("Oppdater", self._show_list,
                          small=True, size_hint_x=0.35))
                self._tool_action_bar.add_widget(
                    mklbl("Karakterer", color=GOLD, size=14, bold=True))
                self._show_list()
            elif self._tool_sub == 'init':
                self._tool_action_bar.add_widget(
                    mklbl("Initiativ-tracker", color=GOLD,
                          size=14, bold=True))
                self._mk_init_tracker()
            else:  # map
                self._tool_action_bar.add_widget(
                    mklbl("Battlemap", color=GOLD,
                          size=14, bold=True))
                self._mk_battle_map()

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
                g.add_widget(mklbl("Ingen karakterer ennå.\nTrykk '+ Ny' for å lage en.",
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
            p = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))

            # Topp: navigasjonsknapper
            top = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            top.add_widget(mkbtn("Tilbake", self._show_list,
                                 small=True, size_hint_x=0.3))
            top.add_widget(mkbtn("Rediger", lambda: self._edit_char(idx),
                                 accent=True, small=True, size_hint_x=0.35))
            top.add_widget(mkbtn("Slett", lambda: self._del_char(idx),
                                 danger=True, small=True, size_hint_x=0.35))
            p.add_widget(top)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(8), padding=dp(4), size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            # ============ HEADER ============
            nm = ch.get('name', '?')
            tp = ch.get('type', 'PC')
            tp_color = GRN if tp == 'PC' else GOLD

            header = RBox(orientation='vertical', bg_color=BG2,
                          size_hint_y=None, height=dp(82),
                          padding=dp(10), spacing=dp(2), radius=dp(12))

            # Navnelinje med type-chip
            name_row = BoxLayout(size_hint_y=None, height=dp(32), spacing=dp(6))
            type_chip = Label(text=tp, font_size=sp(11), color=tp_color,
                              bold=True, size_hint_x=None, width=dp(46))
            name_row.add_widget(type_chip)
            name_lbl = Label(text=nm, font_size=sp(18), color=GOLD, bold=True,
                             halign='left', valign='middle')
            name_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
            name_row.add_widget(name_lbl)
            header.add_widget(name_row)

            # Identitetslinje
            ident_parts = []
            lvl = ch.get('level', '')
            cls = ch.get('class', '')
            if lvl and cls:
                ident_parts.append(f"Nivå {lvl} {cls}")
            elif lvl:
                ident_parts.append(f"Nivå {lvl}")
            elif cls:
                ident_parts.append(cls)
            spc = ch.get('species', '')
            if spc:
                ident_parts.append(spc)
            sub = ch.get('subclass', '')
            if sub:
                ident_parts.append(sub)
            if ident_parts:
                id_lbl = Label(text="  -  ".join(ident_parts),
                               font_size=sp(12), color=TXT,
                               halign='left', valign='middle',
                               size_hint_y=None, height=dp(20))
                id_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
                header.add_widget(id_lbl)

            # Bakgrunn + alignment
            bg_align = []
            bg = ch.get('background', '')
            if bg:
                bg_align.append(bg)
            align = ch.get('alignment', '')
            if align:
                bg_align.append(align)
            if bg_align:
                ba_lbl = Label(text="  -  ".join(bg_align),
                               font_size=sp(11), color=DIM,
                               halign='left', valign='middle',
                               size_hint_y=None, height=dp(18))
                ba_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
                header.add_widget(ba_lbl)

            g.add_widget(header)

            # ============ KAMPBOKS ============
            ab_data = ch.get('abilities', {})
            dex_mod = self._mod(ab_data.get('DEX', {}).get('score', 10))
            pb = ch.get('proficiency_bonus', 2)

            def mk_stat_cell(label, value, color=GOLD):
                """Lite kort med etikett og verdi."""
                fb = RBox(orientation='vertical', bg_color=BG,
                          padding=dp(6), spacing=dp(2), radius=dp(8))
                lb1 = Label(text=label, font_size=sp(9), color=color, bold=True,
                            size_hint_y=None, height=dp(14))
                lb2 = Label(text=str(value), font_size=sp(15), color=TXT, bold=True,
                            size_hint_y=None, height=dp(22))
                fb.add_widget(lb1)
                fb.add_widget(lb2)
                return fb

            combat_box = RBox(orientation='vertical', bg_color=BG2,
                              size_hint_y=None, height=dp(128),
                              padding=dp(10), spacing=dp(6), radius=dp(12))
            combat_box.add_widget(mklbl("KAMP & BEVEGELSE", color=GOLD,
                                        size=11, bold=True, h=18))
            combat_row = BoxLayout(size_hint_y=None, height=dp(54), spacing=dp(6))
            combat_row.add_widget(mk_stat_cell("AC", ch.get('armor_class', 10)))
            combat_row.add_widget(mk_stat_cell(
                "HP", f"{ch.get('hp_current', 0)}/{ch.get('hp_max', 0)}"))
            combat_row.add_widget(mk_stat_cell("INIT", f"{dex_mod:+d}"))
            combat_row.add_widget(mk_stat_cell("FART", ch.get('speed', 30)))
            combat_row.add_widget(mk_stat_cell("PB", f"+{pb}"))
            combat_box.add_widget(combat_row)

            # Status-linje: Temp HP, Hit Dice, Death saves, Inspirasjon
            status_parts = []
            if ch.get('hp_temp'):
                status_parts.append(f"Temp HP: {ch['hp_temp']}")
            hd = ch.get('hit_dice_max', '')
            if hd:
                spent = ch.get('hit_dice_spent', 0)
                status_parts.append(f"HD: {hd} (brukt {spent})")
            ds = ch.get('death_successes', 0)
            df = ch.get('death_failures', 0)
            if ds or df:
                status_parts.append(f"Death: +{ds} -{df}")
            if ch.get('heroic_inspiration'):
                status_parts.append("* Inspirasjon")
            if status_parts:
                sl = Label(text="    ".join(status_parts),
                           font_size=sp(10), color=DIM,
                           halign='left', valign='middle',
                           size_hint_y=None, height=dp(18))
                sl.bind(size=lambda w, v: setattr(w, 'text_size', v))
                combat_box.add_widget(sl)

            g.add_widget(combat_box)

            # ============ EVNEVERDIER ============
            ab_box = RBox(orientation='vertical', bg_color=BG2,
                          size_hint_y=None, height=dp(118),
                          padding=dp(10), spacing=dp(6), radius=dp(12))
            ab_box.add_widget(mklbl("EVNEVERDIER", color=GOLD,
                                    size=11, bold=True, h=18))
            ab_row = BoxLayout(size_hint_y=None, height=dp(74), spacing=dp(4))
            for ab in DND_ABILITIES:
                a = ab_data.get(ab, {})
                score = a.get('score', 10)
                mod = self._mod(score)
                save_bonus = mod + (pb if a.get('save_prof') else 0)
                is_prof = a.get('save_prof', False)

                cell = RBox(orientation='vertical', bg_color=BG,
                            padding=dp(4), spacing=dp(1), radius=dp(8))
                cell.add_widget(Label(text=ab, font_size=sp(10),
                                      color=GOLD, bold=True,
                                      size_hint_y=None, height=dp(14)))
                cell.add_widget(Label(text=str(score), font_size=sp(14),
                                      color=TXT, bold=True,
                                      size_hint_y=None, height=dp(20)))
                cell.add_widget(Label(text=f"{mod:+d}", font_size=sp(11),
                                      color=TXT,
                                      size_hint_y=None, height=dp(16)))
                cell.add_widget(Label(
                    text=f"sv {save_bonus:+d}{'*' if is_prof else ''}",
                    font_size=sp(9),
                    color=GRN if is_prof else DIM,
                    size_hint_y=None, height=dp(14)))
                ab_row.add_widget(cell)
            ab_box.add_widget(ab_row)
            g.add_widget(ab_box)

            # ============ SKILLS ============
            sk_data = ch.get('skills', {})
            prof_skills = [(n, a) for n, a in DND_SKILLS
                           if sk_data.get(n, {}).get('prof')
                           or sk_data.get(n, {}).get('expertise')]
            if prof_skills:
                # Høyde: header + antall rader (2 per rad) × 28
                rows = (len(prof_skills) + 1) // 2
                skbox_h = 28 + rows * 30
                sk_box = RBox(orientation='vertical', bg_color=BG2,
                              size_hint_y=None, height=dp(skbox_h),
                              padding=dp(10), spacing=dp(4), radius=dp(12))
                sk_box.add_widget(mklbl("FERDIGHETER", color=GOLD,
                                        size=11, bold=True, h=18))

                sk_grid = GridLayout(cols=2, spacing=dp(6),
                                     size_hint_y=None)
                sk_grid.bind(minimum_height=sk_grid.setter('height'))
                for sname, sab in prof_skills:
                    sd = sk_data[sname]
                    mod = self._mod(ab_data.get(sab, {}).get('score', 10))
                    bonus = mod + pb * (2 if sd.get('expertise') else 1)
                    star = " *" if sd.get('expertise') else ""

                    cell = BoxLayout(orientation='horizontal',
                                     size_hint_y=None, height=dp(26),
                                     spacing=dp(4), padding=[dp(6), 0])
                    name_lb = Label(text=f"{sname}{star}",
                                    font_size=sp(11), color=TXT,
                                    halign='left', valign='middle')
                    name_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                    cell.add_widget(name_lb)
                    val_lb = Label(text=f"{bonus:+d}", font_size=sp(12),
                                   color=GOLD, bold=True,
                                   size_hint_x=None, width=dp(34),
                                   halign='right', valign='middle')
                    val_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                    cell.add_widget(val_lb)
                    sk_grid.add_widget(cell)
                sk_box.add_widget(sk_grid)
                g.add_widget(sk_box)

            # ============ RUSTNING & SPRÅK ============
            at = ch.get('armor_training', {})
            trained = [k.capitalize() for k in ['light', 'medium', 'heavy', 'shields']
                       if at.get(k)]
            wp = ch.get('weapon_prof', '')
            tp_prof = ch.get('tool_prof', '')
            lang = ch.get('languages', '')

            if trained or wp or tp_prof or lang:
                prof_box = RBox(orientation='vertical', bg_color=BG2,
                                size_hint_y=None,
                                padding=dp(10), spacing=dp(4), radius=dp(12))
                prof_box.add_widget(mklbl("TRENING & SPRÅK", color=GOLD,
                                          size=11, bold=True, h=18))
                prof_h = 28

                def add_prof_line(label, value):
                    nonlocal prof_h
                    if not value:
                        return
                    row = BoxLayout(orientation='horizontal',
                                    size_hint_y=None, spacing=dp(6))
                    lb = Label(text=label + ":", font_size=sp(10),
                               color=DIM, size_hint_x=None, width=dp(90),
                               halign='left', valign='top')
                    lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                    row.add_widget(lb)
                    vl = Label(text=str(value), font_size=sp(11),
                               color=TXT, halign='left', valign='top')
                    vl.bind(width=lambda w, v: setattr(w, 'text_size', (v - dp(4), None)))
                    vl.bind(texture_size=lambda w, ts: setattr(
                        row, 'height', max(dp(22), ts[1] + dp(6))))
                    vl.bind(texture_size=lambda w, ts: setattr(vl, 'height', ts[1]))
                    row.add_widget(vl)
                    row.height = dp(22)
                    prof_box.add_widget(row)
                    prof_h += 28

                if trained:
                    add_prof_line("Rustning", ", ".join(trained))
                if wp:
                    add_prof_line("Våpen", wp)
                if tp_prof:
                    add_prof_line("Verktøy", tp_prof)
                if lang:
                    add_prof_line("Språk", lang)

                prof_box.height = dp(max(50, prof_h))
                g.add_widget(prof_box)

            # ============ VÅPEN, EGENSKAPER, MAGI, BESKRIVELSE ============
            def add_text_section(title, content, color=TXT):
                if not content:
                    return
                lines = str(content).count('\n') + 1
                section_h = 30 + max(lines * 18, 30) + 12
                sec = RBox(orientation='vertical', bg_color=BG2,
                           size_hint_y=None,
                           padding=dp(10), spacing=dp(4), radius=dp(12))
                sec.add_widget(mklbl(title, color=GOLD,
                                     size=11, bold=True, h=18))
                body = Label(text=str(content), font_size=sp(11),
                             color=color, halign='left', valign='top',
                             size_hint_y=None)
                body.bind(width=lambda w, v: setattr(
                    w, 'text_size', (v - dp(4), None)))
                body.bind(texture_size=lambda w, ts: setattr(
                    w, 'height', ts[1]))
                body.bind(texture_size=lambda w, ts: setattr(
                    sec, 'height', ts[1] + dp(36)))
                sec.add_widget(body)
                sec.height = dp(section_h)
                g.add_widget(sec)

            add_text_section("VÅPEN", ch.get('weapons', ''))
            add_text_section("KLASSE-EGENSKAPER", ch.get('class_features', ''))
            add_text_section("SPECIES-TREKK", ch.get('species_traits', ''))
            add_text_section("FEATS", ch.get('feats', ''))

            # ============ MAGI ============
            sa = ch.get('spell_ability', '')
            slots = ch.get('spell_slots', {})
            any_slots = any((slots.get(str(l), {}).get('total', 0) > 0)
                            for l in range(1, 10))
            spells_txt = ch.get('spells', '')
            if sa or any_slots or spells_txt:
                mag_box = RBox(orientation='vertical', bg_color=BG2,
                               size_hint_y=None,
                               padding=dp(10), spacing=dp(6), radius=dp(12))
                mag_box.add_widget(mklbl("MAGI", color=GOLD,
                                         size=11, bold=True, h=18))
                mag_h = 28

                if sa:
                    dc = ch.get('spell_save_dc', 0)
                    ab = ch.get('spell_attack_bonus', 0)
                    stat_row = BoxLayout(size_hint_y=None, height=dp(48),
                                         spacing=dp(6))
                    stat_row.add_widget(mk_stat_cell("EVNE", sa))
                    stat_row.add_widget(mk_stat_cell("SAVE DC", dc))
                    stat_row.add_widget(mk_stat_cell("ATK", f"{ab:+d}"))
                    mag_box.add_widget(stat_row)
                    mag_h += 54

                if any_slots:
                    slot_grid = GridLayout(cols=3, spacing=dp(4),
                                           size_hint_y=None)
                    slot_grid.bind(minimum_height=slot_grid.setter('height'))
                    for lvl in range(1, 10):
                        s = slots.get(str(lvl), {})
                        t = s.get('total', 0)
                        if t > 0:
                            e = s.get('expended', 0)
                            cell = RBox(orientation='horizontal', bg_color=BG,
                                        padding=dp(4), radius=dp(6),
                                        size_hint_y=None, height=dp(24))
                            cell.add_widget(Label(
                                text=f"L{lvl}:", font_size=sp(10),
                                color=GOLD, bold=True,
                                size_hint_x=None, width=dp(28),
                                halign='left', valign='middle'))
                            cell.add_widget(Label(
                                text=f"{t-e}/{t}", font_size=sp(11),
                                color=TXT, halign='right', valign='middle'))
                            slot_grid.add_widget(cell)
                    mag_box.add_widget(slot_grid)
                    num_slot_rows = sum(1 for lvl in range(1, 10)
                                        if slots.get(str(lvl), {}).get('total', 0) > 0)
                    mag_h += ((num_slot_rows + 2) // 3) * 28

                if spells_txt:
                    sp_lines = str(spells_txt).count('\n') + 1
                    sp_h = max(40, sp_lines * 18)
                    sp_lbl = Label(text=str(spells_txt), font_size=sp(11),
                                   color=TXT, halign='left', valign='top',
                                   size_hint_y=None, height=dp(sp_h))
                    sp_lbl.bind(width=lambda w, v: setattr(
                        w, 'text_size', (v - dp(4), None)))
                    sp_lbl.bind(texture_size=lambda w, ts: setattr(
                        w, 'height', ts[1]))
                    mag_box.add_widget(sp_lbl)
                    mag_h += sp_h + 6

                mag_box.height = dp(mag_h + 10)
                g.add_widget(mag_box)

            # ============ UTSEENDE / BAKGRUNN / UTSTYR ============
            add_text_section("UTSEENDE", ch.get('appearance', ''))
            add_text_section("BAKGRUNN", ch.get('backstory', ''))
            add_text_section("UTSTYR", ch.get('equipment', ''))

            # ============ ATTUNEMENT ============
            att = ch.get('attunement', [])
            att_used = [a for a in att if a]
            if att_used:
                att_h = 28 + len(att_used) * 24 + 8
                att_box = RBox(orientation='vertical', bg_color=BG2,
                               size_hint_y=None, height=dp(att_h),
                               padding=dp(10), spacing=dp(4), radius=dp(12))
                att_box.add_widget(mklbl("ATTUNEMENT", color=GOLD,
                                         size=11, bold=True, h=18))
                for a in att_used:
                    al = Label(text=f"- {a}", font_size=sp(11), color=TXT,
                               halign='left', valign='middle',
                               size_hint_y=None, height=dp(22))
                    al.bind(size=lambda w, v: setattr(w, 'text_size', v))
                    att_box.add_widget(al)
                g.add_widget(att_box)

            # ============ MYNTER ============
            coins = ch.get('coins', {})
            if any(coins.get(c, 0) for c in ['cp', 'sp', 'ep', 'gp', 'pp']):
                co_box = RBox(orientation='vertical', bg_color=BG2,
                              size_hint_y=None, height=dp(78),
                              padding=dp(10), spacing=dp(6), radius=dp(12))
                co_box.add_widget(mklbl("MYNTER", color=GOLD,
                                        size=11, bold=True, h=18))
                co_row = BoxLayout(size_hint_y=None, height=dp(42),
                                   spacing=dp(4))
                for c in ['cp', 'sp', 'ep', 'gp', 'pp']:
                    val = coins.get(c, 0)
                    cell = RBox(orientation='vertical', bg_color=BG,
                                padding=dp(4), radius=dp(6))
                    cell.add_widget(Label(text=c.upper(), font_size=sp(9),
                                          color=GOLD, bold=True,
                                          size_hint_y=None, height=dp(14)))
                    cell.add_widget(Label(text=str(val), font_size=sp(12),
                                          color=TXT if val else DIM,
                                          size_hint_y=None, height=dp(18)))
                    co_row.add_widget(cell)
                co_box.add_widget(co_row)
                g.add_widget(co_box)

            # Litt bunn-luft
            g.add_widget(mksep(12))

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
            p = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(8))

            # Topp: Lagre/Avbryt
            top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
            top.add_widget(mkbtn("Lagre", self._save_edit, accent=True,
                                 size_hint_x=0.5))
            top.add_widget(mkbtn("Avbryt", self._show_list,
                                 size_hint_x=0.5))
            p.add_widget(top)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(10), padding=dp(4),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))
            self._ei = {}

            # --- Felles byggefunksjoner ---
            def ti(key, value='', int_only=False, multiline=False,
                   height=38, sx=1):
                txt = '' if value == '' or value is None else str(value)
                w = TextInput(text=txt, font_size=sp(13), multiline=multiline,
                              background_color=INPUT, foreground_color=TXT,
                              cursor_color=GOLD,
                              size_hint_x=sx, padding=[dp(8), dp(6)])
                if int_only:
                    w.input_filter = 'int'
                if multiline:
                    w.size_hint_y = None
                    w.height = dp(height)
                else:
                    w.size_hint_y = None
                    w.height = dp(34)
                self._ei[key] = w
                return w

            def field_lbl(text, sx=None, halign='right', size=11, color=DIM):
                lb = Label(text=text, font_size=sp(size), color=color,
                           halign=halign, valign='middle')
                if sx is not None:
                    lb.size_hint_x = sx
                lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                return lb

            def row(h=36, spacing=8):
                return BoxLayout(size_hint_y=None, height=dp(h),
                                 spacing=dp(spacing))

            def toggle(key, state, width=None):
                """Liten rund toggle. PÅ = gull 'X', AV = tom."""
                t = RToggle(
                    text='X' if state else '',
                    state='down' if state else 'normal',
                    color=GOLD if state else DIM,
                    bg_color=BTNH if state else INPUT,
                    font_size=sp(12), bold=True)
                def _upd(inst, val):
                    on = (val == 'down')
                    inst.text = 'X' if on else ''
                    inst.color = GOLD if on else DIM
                    inst.bg_color = BTNH if on else INPUT
                t.bind(state=_upd)
                if width is not None:
                    t.size_hint_x = None
                    t.width = dp(width)
                self._ei[key] = t
                return t

            def mk_spinner(text, values, sx=1):
                sp_w = Spinner(text=text, values=values,
                               background_color=INPUT, color=GOLD,
                               font_size=sp(12), size_hint_x=sx)
                return sp_w

            def section(title, body_widget_list, height):
                box = RBox(orientation='vertical', bg_color=BG2,
                           size_hint_y=None, height=dp(height),
                           padding=dp(10), spacing=dp(6), radius=dp(12))
                box.add_widget(mklbl(title, color=GOLD,
                                     size=12, bold=True, h=22))
                for w in body_widget_list:
                    box.add_widget(w)
                return box

            # ============ HJELPETEKST ============
            help_box = RBox(orientation='vertical', bg_color=BG2,
                            size_hint_y=None, height=dp(148),
                            padding=dp(12), spacing=dp(4), radius=dp(12))
            help_box.add_widget(mklbl(
                "Slik registrerer du en karakter",
                color=GOLD, size=12, bold=True, h=20))
            help_txt = (
                "1. Fyll inn IDENTITET (navn, species, klasse, nivå).\n"
                "2. Sett Proficiency Bonus (PB) basert på nivå:\n"
                "     Lv 1-4: +2    Lv 5-8: +3    Lv 9-12: +4\n"
                "     Lv 13-16: +5    Lv 17-20: +6\n"
                "3. Sett EVNEVERDIER (ability scores, vanligvis 1-20).\n"
                "     Modifier regnes automatisk som (score-10)/2.\n"
                "4. Huk av 'Sv' for evner der karakteren har save proficiency.\n"
                "5. Under FERDIGHETER, huk av 'Prof' for trente skills.\n"
                "     Huk av 'Exp' i tillegg for expertise (dobbel PB).\n"
                "     Bonus regnes og vises automatisk."
            )
            help_lbl = Label(
                text=help_txt,
                font_size=sp(10), color=TXT,
                halign='left', valign='top',
                size_hint_y=None, height=dp(124))
            help_lbl.bind(width=lambda w, v: setattr(
                w, 'text_size', (v - dp(4), None)))
            help_box.add_widget(help_lbl)
            g.add_widget(help_box)

            # ============ 1. IDENTITET ============
            id_widgets = []

            r = row()
            r.add_widget(field_lbl("Navn", sx=0.22))
            r.add_widget(ti('name', ch.get('name', ''), sx=0.55))
            r.add_widget(field_lbl("Type", sx=0.1))
            tp_sp = mk_spinner(ch.get('type', 'PC'), ['PC', 'NPC'], sx=0.13)
            self._ei['type'] = tp_sp
            r.add_widget(tp_sp)
            id_widgets.append(r)

            r = row()
            r.add_widget(field_lbl("Species", sx=0.22))
            r.add_widget(ti('species', ch.get('species', ''), sx=0.28))
            r.add_widget(field_lbl("Klasse", sx=0.18))
            r.add_widget(ti('class', ch.get('class', ''), sx=0.32))
            id_widgets.append(r)

            r = row()
            r.add_widget(field_lbl("Subklasse", sx=0.22))
            r.add_widget(ti('subclass', ch.get('subclass', ''), sx=0.28))
            r.add_widget(field_lbl("Bakgrunn", sx=0.18))
            r.add_widget(ti('background', ch.get('background', ''), sx=0.32))
            id_widgets.append(r)

            r = row()
            r.add_widget(field_lbl("Nivå", sx=0.15))
            r.add_widget(ti('level', ch.get('level', 1),
                            int_only=True, sx=0.18))
            r.add_widget(field_lbl("XP", sx=0.12))
            r.add_widget(ti('xp', ch.get('xp', 0), int_only=True, sx=0.22))
            r.add_widget(field_lbl("PB", sx=0.12))
            r.add_widget(ti('proficiency_bonus', ch.get('proficiency_bonus', 2),
                            int_only=True, sx=0.21))
            id_widgets.append(r)

            r = row()
            r.add_widget(field_lbl("Alignment", sx=0.3))
            r.add_widget(ti('alignment', ch.get('alignment', ''), sx=0.7))
            id_widgets.append(r)

            g.add_widget(section("IDENTITET", id_widgets, 28 + 5 * 44))

            # ============ 2. KAMP & BEVEGELSE ============
            cb_widgets = []

            r = row()
            r.add_widget(field_lbl("AC", sx=0.1))
            r.add_widget(ti('armor_class', ch.get('armor_class', 10),
                            int_only=True, sx=0.17))
            r.add_widget(field_lbl("Init", sx=0.13))
            r.add_widget(ti('initiative', ch.get('initiative', 0),
                            int_only=True, sx=0.17))
            r.add_widget(field_lbl("Fart", sx=0.13))
            r.add_widget(ti('speed', ch.get('speed', 30),
                            int_only=True, sx=0.15))
            r.add_widget(field_lbl("P.Pers", sx=0.13))
            r.add_widget(ti('passive_perception', ch.get('passive_perception', 10),
                            int_only=True, sx=0.15))
            cb_widgets.append(r)

            r = row()
            r.add_widget(field_lbl("Størrelse", sx=0.28))
            sz_sp = mk_spinner(
                ch.get('size', 'Medium'),
                ['Tiny', 'Small', 'Medium', 'Large', 'Huge', 'Gargantuan'],
                sx=0.4)
            self._ei['size'] = sz_sp
            r.add_widget(sz_sp)
            r.add_widget(field_lbl("Inspirasjon", sx=0.22))
            t = toggle('heroic_inspiration',
                       ch.get('heroic_inspiration', False), width=50)
            r.add_widget(t)
            cb_widgets.append(r)

            g.add_widget(section("KAMP & BEVEGELSE", cb_widgets, 28 + 2 * 44))

            # ============ 3. HIT POINTS ============
            hp_widgets = []

            r = row()
            r.add_widget(field_lbl("HP", sx=0.1))
            r.add_widget(ti('hp_current', ch.get('hp_current', 0),
                            int_only=True, sx=0.22))
            r.add_widget(field_lbl("Max", sx=0.1))
            r.add_widget(ti('hp_max', ch.get('hp_max', 0),
                            int_only=True, sx=0.22))
            r.add_widget(field_lbl("Temp", sx=0.13))
            r.add_widget(ti('hp_temp', ch.get('hp_temp', 0),
                            int_only=True, sx=0.22))
            hp_widgets.append(r)

            r = row()
            r.add_widget(field_lbl("Hit Dice", sx=0.22))
            r.add_widget(ti('hit_dice_max', ch.get('hit_dice_max', '1d8'),
                            sx=0.28))
            r.add_widget(field_lbl("Brukt", sx=0.2))
            r.add_widget(ti('hit_dice_spent', ch.get('hit_dice_spent', 0),
                            int_only=True, sx=0.3))
            hp_widgets.append(r)

            r = row()
            r.add_widget(field_lbl("Dødskast +", sx=0.3))
            r.add_widget(ti('death_successes', ch.get('death_successes', 0),
                            int_only=True, sx=0.2))
            r.add_widget(field_lbl("Dødskast -", sx=0.3))
            r.add_widget(ti('death_failures', ch.get('death_failures', 0),
                            int_only=True, sx=0.2))
            hp_widgets.append(r)

            g.add_widget(section("HIT POINTS & DØDSKAST", hp_widgets,
                                 28 + 3 * 44))

            # ============ 4. EVNEVERDIER (KOMPAKT RUTENETT) ============
            ab_widgets = []
            ab_widgets.append(mklbl(
                "Huk av 'Sv' for save proficiency",
                color=DIM, size=10, h=18))

            # Header-rad
            hr = row(h=20, spacing=4)
            hr.add_widget(field_lbl("Evne", sx=0.2, halign='left',
                                    size=9, color=GDIM))
            hr.add_widget(field_lbl("Score", sx=0.25, halign='center',
                                    size=9, color=GDIM))
            hr.add_widget(field_lbl("Mod", sx=0.2, halign='center',
                                    size=9, color=GDIM))
            hr.add_widget(field_lbl("Save", sx=0.18, halign='center',
                                    size=9, color=GDIM))
            hr.add_widget(field_lbl("Sv", sx=0.17, halign='center',
                                    size=9, color=GDIM))
            ab_widgets.append(hr)

            ab_data = ch.get('abilities', {})
            for ab in DND_ABILITIES:
                ad = ab_data.get(ab, {'score': 10, 'save_prof': False})
                r = row(h=40, spacing=4)

                # Evnekode
                lb = Label(text=ab, font_size=sp(13), color=GOLD, bold=True,
                           halign='left', valign='middle', size_hint_x=0.2)
                lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                r.add_widget(lb)

                # Score-felt
                sc_in = ti(f'ab_{ab}_score', ad.get('score', 10),
                           int_only=True, sx=0.25)
                r.add_widget(sc_in)

                # Modifier (live)
                mod_lb = Label(text=self._fmt_mod(ad.get('score', 10)),
                               font_size=sp(14), color=TXT, bold=True,
                               size_hint_x=0.2,
                               halign='center', valign='middle')
                mod_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                sc_in.bind(text=lambda inst, v, m=mod_lb:
                           setattr(m, 'text', self._fmt_mod(v)))
                r.add_widget(mod_lb)

                # Save-bonus (live, beregnes fra score + PB hvis prof)
                sv_lb = Label(text='', font_size=sp(12), color=DIM,
                              size_hint_x=0.18,
                              halign='center', valign='middle')
                sv_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                r.add_widget(sv_lb)

                # Toggle
                tog = toggle(f'ab_{ab}_save', ad.get('save_prof', False))
                tog.size_hint_x = 0.17
                r.add_widget(tog)

                # Live update save-bonus
                def _upd_save(*_a, ab=ab, sl=sv_lb, si=sc_in, tg=tog):
                    try:
                        score = int(si.text) if si.text else 10
                    except ValueError:
                        score = 10
                    try:
                        pb_w = self._ei.get('proficiency_bonus')
                        pb = int(pb_w.text) if (pb_w and pb_w.text) else 2
                    except (ValueError, AttributeError):
                        pb = 2
                    mod = (score - 10) // 2
                    is_prof = (tg.state == 'down')
                    bonus = mod + (pb if is_prof else 0)
                    sl.text = f"{bonus:+d}"
                    sl.color = GOLD if is_prof else DIM

                _upd_save()
                sc_in.bind(text=_upd_save)
                tog.bind(state=_upd_save)
                pb_w0 = self._ei.get('proficiency_bonus')
                if pb_w0:
                    pb_w0.bind(text=_upd_save)

                ab_widgets.append(r)

            g.add_widget(section("EVNEVERDIER", ab_widgets,
                                 28 + 18 + 24 + 6 * 46))

            # ============ 5. FERDIGHETER ============
            sk_widgets = []
            sk_widgets.append(mklbl(
                "Prof legger til PB, Exp legger til PB to ganger",
                color=DIM, size=10, h=18))

            hr = row(h=20, spacing=4)
            hr.add_widget(field_lbl("Ferdighet", sx=0.5, halign='left',
                                    size=9, color=GDIM))
            hr.add_widget(field_lbl("Prof", sx=0.15, halign='center',
                                    size=9, color=GDIM))
            hr.add_widget(field_lbl("Exp", sx=0.15, halign='center',
                                    size=9, color=GDIM))
            hr.add_widget(field_lbl("Bonus", sx=0.2, halign='center',
                                    size=9, color=GDIM))
            sk_widgets.append(hr)

            sk_data = ch.get('skills', {})
            for sname, sab in DND_SKILLS:
                sd = sk_data.get(sname, {'prof': False, 'expertise': False})
                r = row(h=36, spacing=4)

                name_lb = Label(text=f"{sname} ({sab})",
                                font_size=sp(11), color=TXT,
                                halign='left', valign='middle',
                                size_hint_x=0.5)
                name_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                r.add_widget(name_lb)

                t1 = toggle(f'sk_{sname}_prof', sd.get('prof', False))
                t1.size_hint_x = 0.15
                r.add_widget(t1)
                t2 = toggle(f'sk_{sname}_exp', sd.get('expertise', False))
                t2.size_hint_x = 0.15
                r.add_widget(t2)

                bonus_lb = Label(text='', font_size=sp(13), color=GOLD,
                                 bold=True, size_hint_x=0.2,
                                 halign='center', valign='middle')
                bonus_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                r.add_widget(bonus_lb)

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

                _upd()
                sc_w = self._ei.get(f'ab_{sab}_score')
                if sc_w:
                    sc_w.bind(text=_upd)
                pb_w = self._ei.get('proficiency_bonus')
                if pb_w:
                    pb_w.bind(text=_upd)
                t1.bind(state=_upd)
                t2.bind(state=_upd)

                sk_widgets.append(r)

            g.add_widget(section("FERDIGHETER", sk_widgets,
                                 28 + 18 + 24 + 18 * 42))

            # ============ 6. TRENING & SPRÅK ============
            tr_widgets = []

            at = ch.get('armor_training', {})
            armor_row = row()
            armor_row.add_widget(field_lbl("Rustning", sx=0.26,
                                           halign='left'))
            for a, lbl in [('light', 'Lett'), ('medium', 'Med'),
                           ('heavy', 'Tung'), ('shields', 'Skjold')]:
                cell = BoxLayout(orientation='horizontal',
                                 size_hint_x=0.185, spacing=dp(3))
                lb = Label(text=lbl, font_size=sp(10), color=DIM,
                           halign='right', valign='middle')
                lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                cell.add_widget(lb)
                t = toggle(f'armor_{a}', at.get(a, False), width=34)
                cell.add_widget(t)
                armor_row.add_widget(cell)
            tr_widgets.append(armor_row)

            for k, lbl in [('weapon_prof',  'Våpentrening'),
                           ('tool_prof',    'Verktøy-trening'),
                           ('languages',    'Språk')]:
                tr_widgets.append(mklbl(lbl, color=DIM, size=10, h=18))
                tr_widgets.append(ti(k, ch.get(k, ''),
                                     multiline=True, height=54))

            g.add_widget(section("TRENING & SPRÅK", tr_widgets,
                                 28 + 44 + 3 * (18 + 60)))

            # ============ 7. VÅPEN ============
            wp_widgets = [
                mklbl("Én per linje: Navn | Atk | Skade | Notater",
                      color=DIM, size=10, h=18),
                ti('weapons', ch.get('weapons', ''),
                   multiline=True, height=110),
            ]
            g.add_widget(section("VÅPEN", wp_widgets, 28 + 18 + 118))

            # ============ 8. EGENSKAPER ============
            ef_widgets = []
            for k, lbl in [('class_features',  'Klasse-egenskaper'),
                           ('species_traits',  'Species-trekk'),
                           ('feats',           'Feats')]:
                ef_widgets.append(mklbl(lbl, color=DIM, size=10, h=18))
                ef_widgets.append(ti(k, ch.get(k, ''),
                                     multiline=True, height=80))
            g.add_widget(section("EGENSKAPER", ef_widgets,
                                 28 + 3 * (18 + 86)))

            # ============ 9. MAGI ============
            mg_widgets = []

            r = row()
            r.add_widget(field_lbl("Evne", sx=0.2))
            sa_val = ch.get('spell_ability', '') or '-'
            sa_sp = mk_spinner(sa_val, ['-', 'INT', 'WIS', 'CHA'], sx=0.2)
            self._ei['spell_ability'] = sa_sp
            r.add_widget(sa_sp)
            r.add_widget(field_lbl("Save DC", sx=0.18))
            r.add_widget(ti('spell_save_dc', ch.get('spell_save_dc', 0),
                            int_only=True, sx=0.14))
            r.add_widget(field_lbl("Atk", sx=0.14))
            r.add_widget(ti('spell_attack_bonus', ch.get('spell_attack_bonus', 0),
                            int_only=True, sx=0.14))
            mg_widgets.append(r)

            mg_widgets.append(mklbl(
                "Spell slots — Total / Brukt",
                color=DIM, size=10, h=18))

            slots = ch.get('spell_slots', {})
            for row_start in range(1, 10, 3):
                slot_row = row(h=34, spacing=6)
                for lvl in range(row_start, min(row_start + 3, 10)):
                    s = slots.get(str(lvl), {'total': 0, 'expended': 0})
                    cell = BoxLayout(orientation='horizontal',
                                     size_hint_x=1, spacing=dp(3))
                    lb = Label(text=f"L{lvl}", font_size=sp(10),
                               color=GOLD, bold=True,
                               size_hint_x=None, width=dp(26),
                               halign='center', valign='middle')
                    lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                    cell.add_widget(lb)
                    cell.add_widget(ti(f'slot_{lvl}_total',
                                       s.get('total', 0),
                                       int_only=True, sx=0.5))
                    sep = Label(text="/", font_size=sp(11), color=DIM,
                                size_hint_x=None, width=dp(10))
                    cell.add_widget(sep)
                    cell.add_widget(ti(f'slot_{lvl}_expended',
                                       s.get('expended', 0),
                                       int_only=True, sx=0.5))
                    slot_row.add_widget(cell)
                mg_widgets.append(slot_row)

            mg_widgets.append(mklbl("Cantrips & tilberedte spells",
                                    color=DIM, size=10, h=18))
            mg_widgets.append(ti('spells', ch.get('spells', ''),
                                 multiline=True, height=130))

            g.add_widget(section("MAGI", mg_widgets,
                                 28 + 44 + 18 + 3 * 40 + 18 + 138))

            # ============ 10. BESKRIVELSE ============
            be_widgets = []
            for k, lbl in [('appearance', 'Utseende'),
                           ('backstory',  'Bakgrunn'),
                           ('equipment',  'Utstyr')]:
                be_widgets.append(mklbl(lbl, color=DIM, size=10, h=18))
                be_widgets.append(ti(k, ch.get(k, ''),
                                     multiline=True, height=80))
            g.add_widget(section("BESKRIVELSE", be_widgets,
                                 28 + 3 * (18 + 86)))

            # ============ 11. ATTUNEMENT ============
            att_widgets = [mklbl("Maks 3 magiske gjenstander",
                                 color=DIM, size=10, h=18)]
            att = list(ch.get('attunement', ['', '', '']))
            while len(att) < 3:
                att.append('')
            for i in range(3):
                r = row()
                r.add_widget(field_lbl(f"Slot {i+1}", sx=0.22))
                r.add_widget(ti(f'attune_{i}', att[i], sx=0.78))
                att_widgets.append(r)
            g.add_widget(section("ATTUNEMENT", att_widgets,
                                 28 + 18 + 3 * 44))

            # ============ 12. MYNTER ============
            co_widgets = []
            coins = ch.get('coins', {})
            r = row(h=56)
            for c in ['cp', 'sp', 'ep', 'gp', 'pp']:
                cell = BoxLayout(orientation='vertical',
                                 size_hint_x=0.2, spacing=dp(2))
                lb = Label(text=c.upper(), font_size=sp(10),
                           color=GOLD, bold=True,
                           size_hint_y=None, height=dp(16))
                cell.add_widget(lb)
                cell.add_widget(ti(f'coin_{c}', coins.get(c, 0),
                                   int_only=True, sx=1))
                r.add_widget(cell)
            co_widgets.append(r)
            g.add_widget(section("MYNTER", co_widgets, 28 + 60))

            g.add_widget(mksep(12))

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

        # ---------- INITIATIV-TRACKER ----------
        def _init_tracker_init(self):
            """Initialiser state for initiativ-tracker."""
            if not hasattr(self, '_init_phase'):
                self._init_phase = 'setup'   # 'setup' eller 'active'
                self._init_list = []         # liste av dict: {name, init, dex_mod, type, hp}

        def _mk_init_tracker(self):
            """Bygg initiativ-tracker-UI i karakter-tab."""
            self._init_tracker_init()
            self.tool_area.clear_widgets()
            p = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(6))

            if self._init_phase == 'setup':
                self._init_build_setup(p)
            else:
                self._init_build_active(p)

            self.tool_area.add_widget(p)

        def _init_build_setup(self, p):
            """Setup-fase: velg deltakere og skriv inn initiativ-kast."""
            # Topp-knapper
            top = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
            top.add_widget(mkbtn("+ PC/NPC", self._init_show_char_picker,
                                 accent=True, small=True, size_hint_x=0.33))
            top.add_widget(mkbtn("+ Fiende", self._init_show_enemy_picker,
                                 small=True, size_hint_x=0.33))
            top.add_widget(mkbtn("Tom", self._init_clear_list,
                                 danger=True, small=True, size_hint_x=0.34))
            p.add_widget(top)

            # Hjelpetekst
            p.add_widget(mklbl(
                "Legg til deltakere, skriv inn kast, trykk Fullfor.",
                color=DIM, size=10, h=18))

            # Liste over deltakere
            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(4),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            if not self._init_list:
                g.add_widget(mklbl(
                    "Ingen deltakere. Bruk knappene over.",
                    color=DIM, size=12, h=60))
            else:
                # Header
                hdr = BoxLayout(size_hint_y=None, height=dp(22),
                                spacing=dp(4))
                hdr.add_widget(mklbl("Navn", color=GDIM, size=9, h=20))
                hdr.add_widget(Label(text="Kast", font_size=sp(9),
                                     color=GDIM, size_hint_x=None,
                                     width=dp(60)))
                hdr.add_widget(Label(text="", size_hint_x=None,
                                     width=dp(40)))
                g.add_widget(hdr)

                self._init_inputs = []
                for i, entry in enumerate(self._init_list):
                    row_box = RBox(orientation='horizontal', bg_color=BG2,
                                   size_hint_y=None, height=dp(42),
                                   padding=dp(6), spacing=dp(4), radius=dp(8))

                    # Type-chip (PC/NPC/F)
                    tp = entry.get('type', 'PC')
                    chip_color = GRN if tp == 'PC' else (GOLD if tp == 'NPC' else RED)
                    chip = Label(text=tp, font_size=sp(10), color=chip_color,
                                 bold=True, size_hint_x=None, width=dp(36))
                    row_box.add_widget(chip)

                    # Navn (viser DEX-mod hvis tilgjengelig)
                    nm = entry.get('name', '?')
                    dex_mod = entry.get('dex_mod', 0)
                    if dex_mod != 0:
                        nm_txt = f"{nm}  ({dex_mod:+d})"
                    else:
                        nm_txt = nm
                    nm_lb = Label(text=nm_txt, font_size=sp(12), color=TXT,
                                  halign='left', valign='middle')
                    nm_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                    row_box.add_widget(nm_lb)

                    # Kast-felt
                    init_val = str(entry.get('init', '')) if entry.get('init') is not None else ''
                    roll_inp = TextInput(
                        text=init_val, font_size=sp(13), multiline=False,
                        background_color=INPUT, foreground_color=TXT,
                        cursor_color=GOLD,
                        size_hint_x=None, width=dp(60),
                        padding=[dp(6), dp(6)],
                        input_filter='int')
                    # Husk index
                    roll_inp._init_idx = i
                    roll_inp.bind(text=self._init_on_roll_change)
                    self._init_inputs.append(roll_inp)
                    row_box.add_widget(roll_inp)

                    # Fjern-knapp
                    del_btn = RBtn(text='X', bg_color=BTN, color=RED,
                                   font_size=sp(11), bold=True,
                                   size_hint_x=None, width=dp(36))
                    del_btn.bind(on_release=lambda b, idx=i:
                                 self._init_remove_entry(idx))
                    row_box.add_widget(del_btn)

                    g.add_widget(row_box)

            scroll.add_widget(g)
            p.add_widget(scroll)

            # Bunn: Fullfor + Auto-rull
            bottom = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            bottom.add_widget(mkbtn("Auto-rull alle", self._init_auto_roll,
                                    small=True, size_hint_x=0.5))
            bottom.add_widget(mkbtn("Fullfor", self._init_finish,
                                    accent=True, size_hint_x=0.5))
            p.add_widget(bottom)

        def _init_on_roll_change(self, inst, value):
            """Lagre kast-verdi i _init_list."""
            idx = inst._init_idx
            if 0 <= idx < len(self._init_list):
                try:
                    self._init_list[idx]['init'] = int(value) if value else None
                except ValueError:
                    self._init_list[idx]['init'] = None

        def _init_auto_roll(self):
            """Rull d20 + DEX mod for alle som mangler kast."""
            for entry in self._init_list:
                if entry.get('init') is None:
                    roll = random.randint(1, 20)
                    entry['init'] = roll + entry.get('dex_mod', 0)
            self._mk_init_tracker()

        def _init_show_char_picker(self):
            """Vis PC/NPC-velger - kun karakterer som ikke er i lista."""
            already_in = {e.get('name', '') for e in self._init_list}
            # PC-er og NPC-er separat, PC-er forst
            pcs = [ch for ch in self.chars
                   if ch.get('type', 'PC') == 'PC'
                   and ch.get('name', '') not in already_in]
            npcs = [ch for ch in self.chars
                    if ch.get('type', 'PC') == 'NPC'
                    and ch.get('name', '') not in already_in]

            self.tool_area.clear_widgets()
            p = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(6))

            top = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
            top.add_widget(mkbtn("Tilbake", self._mk_init_tracker,
                                 small=True, size_hint_x=0.3))
            top.add_widget(mklbl("Velg karakter", color=GOLD, size=13,
                                 bold=True))
            p.add_widget(top)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(6), padding=dp(4),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            if pcs:
                g.add_widget(mklbl("SPILLERKARAKTERER (PC)",
                                   color=GRN, size=11, bold=True, h=22))
                for ch in pcs:
                    g.add_widget(self._init_make_char_btn(ch))

            if npcs:
                g.add_widget(mklbl("IKKE-SPILLERKARAKTERER (NPC)",
                                   color=GOLD, size=11, bold=True, h=22))
                for ch in npcs:
                    g.add_widget(self._init_make_char_btn(ch))

            if not pcs and not npcs:
                g.add_widget(mklbl(
                    "Ingen tilgjengelige karakterer.\n"
                    "Legg til karakterer under 'Karakterer'-fanen forst.",
                    color=DIM, size=11, h=60))

            scroll.add_widget(g)
            p.add_widget(scroll)
            self.tool_area.add_widget(p)

        def _init_make_char_btn(self, ch):
            """Lag knapp for en karakter i picker-liste."""
            nm = ch.get('name', '?')
            lvl = ch.get('level', '')
            cls = ch.get('class', '')
            sub = " - ".join(s for s in [f"Lv {lvl}" if lvl else "", cls] if s)
            txt = f"{nm}  ({sub})" if sub else nm
            b = mkbtn(txt, lambda c=ch: self._init_add_character(c),
                      small=True)
            b.halign = 'left'
            b.size_hint_y = None
            b.height = dp(42)
            return b

        def _init_add_character(self, ch):
            """Legg til karakter i initiativ-lista."""
            dex_score = ch.get('abilities', {}).get('DEX', {}).get('score', 10)
            dex_mod = (dex_score - 10) // 2
            self._init_list.append({
                'name': ch.get('name', '?'),
                'type': ch.get('type', 'PC'),
                'dex_mod': dex_mod,
                'init': None,
                'hp': f"{ch.get('hp_current', 0)}/{ch.get('hp_max', 0)}",
            })
            self._mk_init_tracker()

        # Vanlige fiender fra D&D 5e monsterliste
        COMMON_ENEMIES = [
            # (navn, DEX-mod, HP)
            ("Goblin", 2, 7),
            ("Hobgoblin", 1, 11),
            ("Bugbear", 2, 27),
            ("Orc", 1, 15),
            ("Orc Chief", 1, 15),
            ("Kobold", 2, 5),
            ("Gnoll", 1, 22),
            ("Bandit", 1, 11),
            ("Bandit Captain", 3, 65),
            ("Cultist", 0, 9),
            ("Cult Fanatic", 1, 33),
            ("Thug", 0, 32),
            ("Guard", 1, 11),
            ("Knight", 0, 52),
            ("Veteran", 1, 58),
            ("Skeleton", 2, 13),
            ("Zombie", -2, 22),
            ("Ghoul", 2, 22),
            ("Ghost", 0, 45),
            ("Wight", 0, 45),
            ("Specter", 2, 22),
            ("Wraith", 3, 67),
            ("Mummy", -1, 58),
            ("Vampire Spawn", 3, 82),
            ("Wolf", 2, 11),
            ("Dire Wolf", 2, 37),
            ("Bear (Brown)", 0, 34),
            ("Giant Spider", 3, 26),
            ("Giant Rat", 2, 7),
            ("Giant Scorpion", 1, 52),
            ("Owlbear", 1, 59),
            ("Troll", 1, 84),
            ("Ogre", -1, 59),
            ("Hill Giant", -1, 105),
            ("Stone Giant", 2, 126),
            ("Frost Giant", -1, 138),
            ("Fire Giant", -1, 162),
            ("Cloud Giant", 0, 200),
            ("Drow", 2, 13),
            ("Dryad", 1, 22),
            ("Satyr", 3, 31),
            ("Harpy", 1, 38),
            ("Medusa", 2, 127),
            ("Minotaur", 0, 76),
            ("Werewolf", 2, 58),
            ("Wereboar", 0, 78),
            ("Demon (Dretch)", 0, 18),
            ("Demon (Quasit)", 3, 7),
            ("Imp", 3, 10),
            ("Succubus", 3, 66),
            ("Pit Fiend", 2, 300),
            ("Dragon (Wyrmling White)", 0, 32),
            ("Dragon (Young Red)", 0, 178),
            ("Dragon (Adult Red)", 0, 256),
            ("Beholder", 2, 180),
            ("Lich", 3, 135),
            ("Elemental (Fire)", 3, 102),
            ("Elemental (Water)", 2, 114),
            ("Elemental (Earth)", -1, 126),
            ("Elemental (Air)", 5, 90),
            ("Mimic", 1, 58),
            ("Doppelganger", 4, 52),
            ("Rust Monster", 1, 27),
            ("Gelatinous Cube", -4, 84),
            ("Shambling Mound", -1, 136),
        ]

        def _init_show_enemy_picker(self):
            """Vis liste over vanlige D&D-fiender + egendefinert."""
            self.tool_area.clear_widgets()
            p = BoxLayout(orientation='vertical', spacing=dp(6), padding=dp(6))

            top = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
            top.add_widget(mkbtn("Tilbake", self._mk_init_tracker,
                                 small=True, size_hint_x=0.3))
            top.add_widget(mklbl("Velg fiende", color=GOLD, size=13,
                                 bold=True))
            p.add_widget(top)

            # Egendefinert navn-felt
            cust_box = RBox(orientation='vertical', bg_color=BG2,
                            size_hint_y=None, height=dp(110),
                            padding=dp(10), spacing=dp(6), radius=dp(10))
            cust_box.add_widget(mklbl("Egendefinert fiende",
                                      color=GOLD, size=11, bold=True, h=18))

            name_row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
            name_row.add_widget(Label(text="Navn:", font_size=sp(11),
                                      color=DIM, size_hint_x=0.2,
                                      halign='right', valign='middle'))
            self._init_custom_name = TextInput(
                text='', font_size=sp(12), multiline=False,
                background_color=INPUT, foreground_color=TXT,
                cursor_color=GOLD, padding=[dp(8), dp(6)],
                size_hint_x=0.8)
            name_row.add_widget(self._init_custom_name)
            cust_box.add_widget(name_row)

            stat_row = BoxLayout(size_hint_y=None, height=dp(34), spacing=dp(6))
            stat_row.add_widget(Label(text="DEX-mod:", font_size=sp(10),
                                      color=DIM, size_hint_x=0.22,
                                      halign='right', valign='middle'))
            self._init_custom_dex = TextInput(
                text='0', font_size=sp(12), multiline=False,
                background_color=INPUT, foreground_color=TXT,
                cursor_color=GOLD, padding=[dp(8), dp(6)],
                size_hint_x=0.15, input_filter='int')
            stat_row.add_widget(self._init_custom_dex)

            add_btn = mkbtn("Legg til", self._init_add_custom,
                            accent=True, small=True, size_hint_x=0.4)
            stat_row.add_widget(Widget(size_hint_x=0.08))
            stat_row.add_widget(add_btn)
            stat_row.add_widget(Widget(size_hint_x=0.15))
            cust_box.add_widget(stat_row)

            p.add_widget(cust_box)

            # Vanlige fiender
            p.add_widget(mklbl("Vanlige D&D-fiender",
                               color=GOLD, size=11, bold=True, h=22))

            scroll = ScrollView()
            g = GridLayout(cols=2, spacing=dp(4), padding=dp(4),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            for name, dex_mod, hp in self.COMMON_ENEMIES:
                mod_str = f" ({dex_mod:+d})" if dex_mod else ""
                txt = f"{name}{mod_str}"
                b = mkbtn(txt,
                          lambda n=name, d=dex_mod, h=hp:
                              self._init_add_enemy(n, d, h),
                          small=True)
                b.size_hint_y = None
                b.height = dp(40)
                b.halign = 'left'
                b.font_size = sp(10)
                g.add_widget(b)

            scroll.add_widget(g)
            p.add_widget(scroll)
            self.tool_area.add_widget(p)

        def _init_add_enemy(self, name, dex_mod, hp):
            """Legg til fiende fra lista. Inkrement hvis duplicate."""
            final_name = name
            existing = [e.get('name', '') for e in self._init_list]
            if final_name in existing:
                # Legg til nummer (Goblin -> Goblin 2, 3, ...)
                n = 2
                while f"{name} {n}" in existing:
                    n += 1
                final_name = f"{name} {n}"

            self._init_list.append({
                'name': final_name,
                'type': 'F',
                'dex_mod': dex_mod,
                'init': None,
                'hp': str(hp) if hp else '',
            })
            self._mk_init_tracker()

        def _init_add_custom(self):
            """Legg til egendefinert fiende."""
            name = self._init_custom_name.text.strip()
            if not name:
                return
            try:
                dex_mod = int(self._init_custom_dex.text or '0')
            except ValueError:
                dex_mod = 0
            self._init_add_enemy(name, dex_mod, '')

        def _init_remove_entry(self, idx):
            """Fjern en deltaker fra lista."""
            if 0 <= idx < len(self._init_list):
                self._init_list.pop(idx)
                self._mk_init_tracker()

        def _init_clear_list(self):
            """Tom hele lista."""
            self._init_list = []
            self._init_phase = 'setup'
            self._mk_init_tracker()

        def _init_finish(self):
            """Gaa fra setup til active: sorter liste etter init."""
            # Fyll inn 0 for de som mangler kast
            for entry in self._init_list:
                if entry.get('init') is None:
                    entry['init'] = 0
            # Sorter hoeyest forst, tiebreaker: DEX-mod
            self._init_list.sort(
                key=lambda e: (e.get('init', 0), e.get('dex_mod', 0)),
                reverse=True)
            self._init_phase = 'active'
            self._mk_init_tracker()

        def _init_build_active(self, p):
            """Aktiv fase: vis sortert rekkefoelge, toppen er aktiv."""
            # Topp-knapper
            top = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
            top.add_widget(mkbtn("Ny runde", self._init_new_encounter,
                                 danger=True, small=True, size_hint_x=0.4))
            top.add_widget(mkbtn("Rediger", self._init_back_to_setup,
                                 small=True, size_hint_x=0.3))
            top.add_widget(mklbl("Initiativ", color=GOLD, size=13, bold=True))
            p.add_widget(top)

            p.add_widget(mklbl(
                "Trykk paa aktiv (oeverst) for aa avslutte turen.",
                color=DIM, size=10, h=18))

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(6), padding=dp(4),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            for i, entry in enumerate(self._init_list):
                is_active = (i == 0)

                # Kortet
                bg = BTNH if is_active else BG2
                box = RBox(orientation='horizontal',
                           bg_color=bg,
                           size_hint_y=None, height=dp(56) if is_active else dp(46),
                           padding=dp(10), spacing=dp(8), radius=dp(10))

                # Init-verdi stor
                init_val = entry.get('init', 0)
                init_lb = Label(
                    text=str(init_val),
                    font_size=sp(18) if is_active else sp(15),
                    color=GOLD if is_active else TXT,
                    bold=True,
                    size_hint_x=None, width=dp(46),
                    halign='center', valign='middle')
                init_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                box.add_widget(init_lb)

                # Type-chip
                tp = entry.get('type', 'PC')
                chip_color = GRN if tp == 'PC' else (GOLD if tp == 'NPC' else RED)
                chip = Label(text=tp, font_size=sp(10), color=chip_color,
                             bold=True,
                             size_hint_x=None, width=dp(30))
                box.add_widget(chip)

                # Navn
                nm = entry.get('name', '?')
                dex_mod = entry.get('dex_mod', 0)
                nm_lb = Label(
                    text=nm,
                    font_size=sp(15) if is_active else sp(12),
                    color=TXT,
                    bold=is_active,
                    halign='left', valign='middle')
                nm_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                box.add_widget(nm_lb)

                # HP (hvis satt)
                hp = entry.get('hp', '')
                if hp:
                    hp_lb = Label(text=f"HP {hp}", font_size=sp(10),
                                  color=DIM,
                                  size_hint_x=None, width=dp(70),
                                  halign='right', valign='middle')
                    hp_lb.bind(size=lambda w, v: setattr(w, 'text_size', v))
                    box.add_widget(hp_lb)

                # Hele kortet er trykkbart (for aa avslutte tur)
                # Bind trykk paa hele boksen
                if is_active:
                    box.bind(on_touch_down=lambda w, t, idx=i:
                             self._init_on_card_touch(w, t, idx))

                g.add_widget(box)

            scroll.add_widget(g)
            p.add_widget(scroll)

        def _init_on_card_touch(self, widget, touch, idx):
            """Haandter trykk paa kort - kun hvis det er aktive/oeverste."""
            if not widget.collide_point(*touch.pos):
                return False
            if idx == 0:
                # Flytt oeverste til bunnen (dens tur er ferdig)
                top_entry = self._init_list.pop(0)
                self._init_list.append(top_entry)
                self._mk_init_tracker()
                return True
            return False

        def _init_new_encounter(self):
            """Start ny runde - tom lista og gaa tilbake til setup."""
            self._init_list = []
            self._init_phase = 'setup'
            self._mk_init_tracker()

        def _init_back_to_setup(self):
            """Gaa tilbake til setup (behold lista)."""
            # Nullstill init-verdier saa de kan rulles paa nytt
            for entry in self._init_list:
                entry['init'] = None
            self._init_phase = 'setup'
            self._mk_init_tracker()

        # ============================================================
        # BATTLEMAP
        # ============================================================
        def _battle_state_init(self):
            """Initialiser battlemap-tilstand (en gang per app-kjøring)."""
            if hasattr(self, '_bm_init_done'):
                return
            self._bm_init_done = True
            # Last lagret tilstand hvis finnes
            saved = load_json(BATTLE_FILE, {})
            self._bm_bg = saved.get('bg', None)          # sti til bakgrunn
            self._bm_grid_cols = saved.get('cols', 20)
            self._bm_show_grid = saved.get('show_grid', True)
            self._bm_tokens = saved.get('tokens', [])
            self._bm_fog = saved.get('fog', [])          # liste av [col,row]
            self._bm_mode = 'move'                       # 'move','fog','measure'
            self._bm_sel_token = None                    # idx i _bm_tokens
            self._bm_measure_start = None                # [col,row]
            self._bm_last_info = ""
            self._bm_cast_counter = 0

        def _battle_cell_size(self):
            """Beregn px/rute basert paa kolonner og canvas-bredde."""
            return CANVAS_W // self._bm_grid_cols

        def _battle_grid_rows(self):
            """Antall rader som faar plass."""
            return CANVAS_H // self._battle_cell_size()

        def _battle_save(self):
            """Lagre battlemap-tilstand til JSON."""
            save_json(BATTLE_FILE, {
                'bg': self._bm_bg,
                'cols': self._bm_grid_cols,
                'show_grid': self._bm_show_grid,
                'tokens': self._bm_tokens,
                'fog': self._bm_fog,
            })

        def _mk_battle_map(self):
            """Bygg Kart-sub-fanen."""
            self._battle_state_init()
            self.tool_area.clear_widgets()

            if not PIL_OK:
                self.tool_area.add_widget(mklbl(
                    "PIL (Pillow) er ikke tilgjengelig.\n"
                    "Battlemap krever PIL.",
                    color=RED, size=12))
                return

            p = BoxLayout(orientation='vertical', spacing=dp(4),
                          padding=dp(4))

            # MODUS-RAD
            mode_row = BoxLayout(size_hint_y=None, height=dp(40),
                                 spacing=dp(4))
            for m_key, m_txt in [('move','Flytt'),('fog','Taake'),
                                 ('measure','Maal')]:
                active = (self._bm_mode == m_key)
                b = RToggle(text=m_txt, group='bm_mode',
                            state='down' if active else 'normal',
                            bg_color=BTNH if active else BTN,
                            color=GOLD if active else DIM,
                            font_size=sp(11), bold=True)
                b.bind(on_release=lambda x, k=m_key:
                       self._battle_mode_switch(k))
                mode_row.add_widget(b)
            menu_btn = RBtn(text="Meny", bg_color=BTN, color=TXT,
                            font_size=sp(11), bold=True,
                            size_hint_x=0.3)
            menu_btn.bind(on_release=lambda b: self._battle_show_menu())
            mode_row.add_widget(menu_btn)
            p.add_widget(mode_row)

            # KARTBILDE (generer og vis)
            self._battle_render()

            map_box = RBox(bg_color=BLK, radius=dp(8))
            self._bm_img = _BMImage(
                source=BATTLE_PNG,
                allow_stretch=True,
                keep_ratio=True,
                nocache=True,  # force reload ved endring
                touch_cb=self._battle_on_map_touch)
            map_box.add_widget(self._bm_img)
            p.add_widget(map_box)

            # INFO + NESTE-rad
            bot = BoxLayout(size_hint_y=None, height=dp(40),
                            spacing=dp(6), padding=[dp(4), 0])
            self._bm_info_lbl = Label(
                text=self._bm_last_info or self._battle_default_hint(),
                font_size=sp(10), color=DIM,
                halign='left', valign='middle')
            self._bm_info_lbl.bind(
                size=lambda w, v: setattr(w, 'text_size', v))
            bot.add_widget(self._bm_info_lbl)

            nxt = RBtn(text="Neste", bg_color=BTNH, color=GOLD,
                       font_size=sp(12), bold=True,
                       size_hint_x=None, width=dp(80))
            nxt.bind(on_release=lambda b: self._battle_next_turn())
            bot.add_widget(nxt)
            p.add_widget(bot)

            self.tool_area.add_widget(p)

        def _battle_default_hint(self):
            """Hjelpe-tekst for gjeldende modus."""
            if self._bm_mode == 'move':
                if self._bm_sel_token is None:
                    return "Flytt: trykk token for aa velge."
                t = self._bm_tokens[self._bm_sel_token]
                return f"Valgt: {t.get('name','?')}. Trykk rute for aa flytte."
            elif self._bm_mode == 'fog':
                return "Taake: trykk rute for aa slaa av/paa."
            else:
                if self._bm_measure_start is None:
                    return "Maal: trykk startpunkt."
                return "Maal: trykk sluttpunkt."

        def _battle_update_info(self, txt=None):
            """Oppdater info-label uten aa bygge hele UI paa nytt."""
            if txt is None:
                txt = self._battle_default_hint()
            self._bm_last_info = txt
            if hasattr(self, '_bm_info_lbl') and self._bm_info_lbl:
                self._bm_info_lbl.text = txt

        def _battle_refresh_img(self):
            """Rerender + force reload av Kivy-bildet."""
            self._battle_render()
            if hasattr(self, '_bm_img') and self._bm_img:
                self._bm_img.reload()

        def _battle_mode_switch(self, mode):
            """Bytt mellom flytt / taake / maal."""
            self._bm_mode = mode
            self._bm_sel_token = None
            self._bm_measure_start = None
            self._battle_refresh_img()
            self._battle_update_info()

        def _battle_on_map_touch(self, cx, cy):
            """Trykk paa kartet (canvas-piksler). Konverter til grid."""
            cell = self._battle_cell_size()
            cols = self._bm_grid_cols
            rows = self._battle_grid_rows()
            col = int(cx // cell)
            row = int(cy // cell)
            if not (0 <= col < cols and 0 <= row < rows):
                return

            if self._bm_mode == 'move':
                self._battle_handle_move_tap(col, row)
            elif self._bm_mode == 'fog':
                self._battle_toggle_fog(col, row)
            else:
                self._battle_handle_measure_tap(col, row)

        def _battle_handle_move_tap(self, col, row):
            """Move-modus: valg av token eller flytting."""
            # Sjekk om det er token paa denne ruta
            hit = None
            for i, t in enumerate(self._bm_tokens):
                if t.get('col') == col and t.get('row') == row:
                    hit = i
                    break

            if hit is not None:
                # Velg/bytt token
                self._bm_sel_token = hit
                self._battle_refresh_img()
                t = self._bm_tokens[hit]
                self._battle_update_info(
                    f"Valgt: {t.get('name','?')}. "
                    f"Trykk rute for aa flytte.")
                return

            # Tom rute - flytt hvis token er valgt
            if self._bm_sel_token is not None:
                t = self._bm_tokens[self._bm_sel_token]
                dc = col - t.get('col', 0)
                dr = row - t.get('row', 0)
                # D&D diagonal forenklet: Chebyshev-distanse
                squares = max(abs(dc), abs(dr))
                feet = squares * FT_PER_SQUARE
                t['col'] = col
                t['row'] = row
                self._bm_sel_token = None
                self._battle_refresh_img()
                self._battle_update_info(
                    f"{t.get('name','?')} flyttet {feet} ft "
                    f"({squares} ruter).")

        def _battle_toggle_fog(self, col, row):
            """Slaa taake av/paa for en rute."""
            cell = [col, row]
            # fog lagres som liste av [col,row]
            if cell in self._bm_fog:
                self._bm_fog.remove(cell)
            else:
                self._bm_fog.append(cell)
            self._battle_refresh_img()

        def _battle_handle_measure_tap(self, col, row):
            """Maalemodus: to trykk gir avstand."""
            if self._bm_measure_start is None:
                self._bm_measure_start = [col, row]
                self._battle_refresh_img()
                self._battle_update_info(
                    f"Start: ({col},{row}). Trykk sluttpunkt.")
            else:
                sc, sr = self._bm_measure_start
                dc = col - sc
                dr = row - sr
                squares = max(abs(dc), abs(dr))
                feet = squares * FT_PER_SQUARE
                self._battle_update_info(
                    f"Avstand: {feet} ft ({squares} ruter).")
                self._bm_measure_start = None
                self._battle_refresh_img()

        def _battle_next_turn(self):
            """Flytt oeverste i init-lista til bunnen + nullstill valg."""
            if not self._init_list:
                self._battle_update_info(
                    "Ingen initiativ-liste. Legg til deltakere foerst.")
                return
            top = self._init_list.pop(0)
            self._init_list.append(top)
            self._bm_sel_token = None
            self._battle_refresh_img()
            # Vis hvem sin tur det er naa
            new_top = self._init_list[0]
            self._battle_update_info(
                f"Tur: {new_top.get('name','?')}")

        # ---------- BATTLEMAP RENDERING ----------
        def _battle_color_for_type(self, tp):
            """Hent RGB-tuple for token-type."""
            if tp == 'PC':
                return (140, 200, 107)      # groenn
            elif tp == 'NPC':
                return (255, 217, 115)      # gull
            else:
                return (217, 89, 64)        # roed

        def _battle_render(self):
            """Komponer PNG av kartet med PIL."""
            if not PIL_OK:
                return
            try:
                cell = self._battle_cell_size()
                cols = self._bm_grid_cols
                rows = self._battle_grid_rows()
                w = cols * cell
                h = rows * cell

                # Base: bakgrunn eller svart
                if self._bm_bg and os.path.exists(self._bm_bg):
                    try:
                        bg = PILImage.open(self._bm_bg).convert('RGB')
                        bg = bg.resize((w, h))
                        img = bg
                    except Exception as e:
                        log(f"Battlemap bg load error: {e}")
                        img = PILImage.new('RGB', (w, h), (20, 30, 25))
                else:
                    img = PILImage.new('RGB', (w, h), (20, 30, 25))

                draw = PILDraw.Draw(img, 'RGBA')

                # GRID
                if self._bm_show_grid:
                    grid_col = (255, 217, 115, 100)   # dempet gull
                    for c in range(cols + 1):
                        x = c * cell
                        draw.line([(x, 0), (x, h)], fill=grid_col, width=1)
                    for r in range(rows + 1):
                        y = r * cell
                        draw.line([(0, y), (w, y)], fill=grid_col, width=1)

                # TAAKE (semi-transparent moerk)
                fog_col = (10, 10, 15, 210)
                for fc in self._bm_fog:
                    fx, fy = fc[0] * cell, fc[1] * cell
                    draw.rectangle(
                        [(fx, fy), (fx + cell, fy + cell)],
                        fill=fog_col)

                # MAAL-LINJE
                if (self._bm_mode == 'measure'
                        and self._bm_measure_start is not None):
                    sc, sr = self._bm_measure_start
                    sx = sc * cell + cell // 2
                    sy = sr * cell + cell // 2
                    draw.ellipse(
                        [(sx - cell // 3, sy - cell // 3),
                         (sx + cell // 3, sy + cell // 3)],
                        outline=(255, 217, 115, 255), width=3)

                # TOKENS
                for i, t in enumerate(self._bm_tokens):
                    tc = t.get('col', 0)
                    tr = t.get('row', 0)
                    if tc < 0 or tc >= cols or tr < 0 or tr >= rows:
                        continue
                    sz = t.get('size', 1)
                    px = tc * cell
                    py = tr * cell
                    tw = cell * sz
                    color = self._battle_color_for_type(
                        t.get('type', 'F'))
                    # Sirkel
                    pad = max(2, cell // 10)
                    draw.ellipse(
                        [(px + pad, py + pad),
                         (px + tw - pad, py + tw - pad)],
                        fill=color + (230,),
                        outline=(0, 0, 0, 255),
                        width=2)
                    # Seleksjon-ring
                    if i == self._bm_sel_token:
                        draw.ellipse(
                            [(px + 1, py + 1),
                             (px + tw - 1, py + tw - 1)],
                            outline=(255, 217, 115, 255), width=4)
                    # Navn (initialer)
                    nm = t.get('name', '?')
                    initials = ''.join(
                        [w[0] for w in nm.split()[:2] if w])[:2].upper()
                    if initials:
                        try:
                            font = PILFont.load_default()
                            tx = px + tw // 2
                            ty = py + tw // 2
                            # Anslaa tekstst enkelt
                            draw.text((tx - 6, ty - 6), initials,
                                      fill=(0, 0, 0, 255), font=font)
                        except Exception:
                            pass

                # Lagre
                img.save(BATTLE_PNG, 'PNG')
            except Exception as e:
                log(f"Battlemap render error: {e}")
                log(traceback.format_exc())

        # ---------- BATTLEMAP MENY + HANDLINGER ----------
        def _battle_show_menu(self):
            """Vis handlings-overlay."""
            self.tool_area.clear_widgets()
            p = BoxLayout(orientation='vertical',
                          spacing=dp(6), padding=dp(6))

            top = BoxLayout(size_hint_y=None, height=dp(42),
                            spacing=dp(6))
            top.add_widget(mkbtn("Tilbake", self._mk_battle_map,
                                 small=True, size_hint_x=0.3))
            top.add_widget(mklbl("Battlemap-meny",
                                 color=GOLD, size=13, bold=True))
            p.add_widget(top)

            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(6), padding=dp(4),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            # BAKGRUNN
            g.add_widget(mklbl("BAKGRUNN", color=GDIM,
                               size=10, bold=True, h=20))
            bg_row = BoxLayout(size_hint_y=None, height=dp(42),
                               spacing=dp(6))
            bg_row.add_widget(mkbtn(
                "Velg bakgrunn", self._battle_pick_bg,
                accent=True, small=True, size_hint_x=0.6))
            bg_row.add_widget(mkbtn(
                "Fjern", self._battle_clear_bg,
                danger=True, small=True, size_hint_x=0.4))
            g.add_widget(bg_row)

            cur_bg = (os.path.basename(self._bm_bg)
                      if self._bm_bg else "(ingen)")
            g.add_widget(mklbl(f"Naa: {cur_bg}", color=DIM,
                               size=10, h=18))

            # RUTENETT
            g.add_widget(mklbl("RUTENETT", color=GDIM,
                               size=10, bold=True, h=20))
            grid_tog = BoxLayout(size_hint_y=None, height=dp(42),
                                 spacing=dp(6))
            txt_tg = ("Skjul rutenett" if self._bm_show_grid
                      else "Vis rutenett")
            grid_tog.add_widget(mkbtn(
                txt_tg, self._battle_toggle_grid,
                small=True, size_hint_x=0.5))
            g.add_widget(grid_tog)

            # KOLONNER (rutestorrelse)
            g.add_widget(mklbl(
                f"Kolonner: {self._bm_grid_cols}  "
                f"(rader: {self._battle_grid_rows()})",
                color=DIM, size=11, h=20))
            col_row = BoxLayout(size_hint_y=None, height=dp(42),
                                spacing=dp(4))
            for n in [10, 15, 20, 25, 30]:
                btn = mkbtn(
                    str(n),
                    lambda x=n: self._battle_set_cols(x),
                    accent=(n == self._bm_grid_cols),
                    small=True)
                col_row.add_widget(btn)
            g.add_widget(col_row)

            # TAAKE
            g.add_widget(mklbl("TAAKE", color=GDIM,
                               size=10, bold=True, h=20))
            fog_row = BoxLayout(size_hint_y=None, height=dp(42),
                                spacing=dp(6))
            fog_row.add_widget(mkbtn(
                "Dekk alt", self._battle_fill_fog,
                small=True, size_hint_x=0.5))
            fog_row.add_widget(mkbtn(
                "Fjern alt", self._battle_clear_fog,
                danger=True, small=True, size_hint_x=0.5))
            g.add_widget(fog_row)

            # TOKENS
            g.add_widget(mklbl("TOKENS", color=GDIM,
                               size=10, bold=True, h=20))
            tok_row = BoxLayout(size_hint_y=None, height=dp(42),
                                spacing=dp(6))
            tok_row.add_widget(mkbtn(
                "+ Fra initiativ", self._battle_sync_from_init,
                accent=True, small=True, size_hint_x=0.6))
            tok_row.add_widget(mkbtn(
                "Tom", self._battle_clear_tokens,
                danger=True, small=True, size_hint_x=0.4))
            g.add_widget(tok_row)

            n_tok = len(self._bm_tokens)
            g.add_widget(mklbl(
                f"Antall tokens paa kartet: {n_tok}",
                color=DIM, size=10, h=18))

            # CAST
            g.add_widget(mklbl("CASTING", color=GDIM,
                               size=10, bold=True, h=20))
            cast_row = BoxLayout(size_hint_y=None, height=dp(42),
                                 spacing=dp(6))
            cast_row.add_widget(mkbtn(
                "Cast til TV", self._battle_cast,
                accent=True, small=True, size_hint_x=0.5))
            g.add_widget(cast_row)

            scroll.add_widget(g)
            p.add_widget(scroll)
            self.tool_area.add_widget(p)

        def _battle_toggle_grid(self):
            self._bm_show_grid = not self._bm_show_grid
            self._battle_show_menu()   # rerender meny-tekst
            # og selve kartet neste gang

        def _battle_set_cols(self, n):
            """Endre antall kolonner. Kast alle tokens utenfor."""
            self._bm_grid_cols = n
            cols = n
            rows = self._battle_grid_rows()
            # Fjern tokens som havner utenfor
            self._bm_tokens = [
                t for t in self._bm_tokens
                if (0 <= t.get('col', 0) < cols
                    and 0 <= t.get('row', 0) < rows)]
            # Fjern fog utenfor
            self._bm_fog = [
                c for c in self._bm_fog
                if 0 <= c[0] < cols and 0 <= c[1] < rows]
            self._battle_show_menu()

        def _battle_fill_fog(self):
            """Dekk hele kartet med taake."""
            cols = self._bm_grid_cols
            rows = self._battle_grid_rows()
            self._bm_fog = [[c, r]
                            for c in range(cols)
                            for r in range(rows)]
            self._battle_show_menu()

        def _battle_clear_fog(self):
            self._bm_fog = []
            self._battle_show_menu()

        def _battle_clear_tokens(self):
            self._bm_tokens = []
            self._bm_sel_token = None
            self._battle_show_menu()

        def _battle_clear_bg(self):
            self._bm_bg = None
            self._battle_show_menu()

        def _battle_sync_from_init(self):
            """Hent tokens fra initiativ-lista. Behold eksisterende posisjoner."""
            if not self._init_list:
                self._battle_update_info(
                    "Ingen initiativ-liste.")
                self._mk_battle_map()
                return

            # Map eksisterende tokens etter navn -> pos
            existing_pos = {}
            for t in self._bm_tokens:
                existing_pos[t.get('name', '')] = (
                    t.get('col', 0), t.get('row', 0))

            cols = self._bm_grid_cols
            # Plassering: PC i venstre kolonne, fiender i hoeyre
            pc_placed = 0
            foe_placed = 0
            new_tokens = []
            for entry in self._init_list:
                nm = entry.get('name', '?')
                tp = entry.get('type', 'F')
                if nm in existing_pos:
                    c, r = existing_pos[nm]
                else:
                    if tp == 'PC':
                        c = 1
                        r = 1 + pc_placed
                        pc_placed += 1
                    else:
                        c = cols - 2
                        r = 1 + foe_placed
                        foe_placed += 1
                new_tokens.append({
                    'name': nm, 'type': tp,
                    'col': c, 'row': r, 'size': 1,
                })
            self._bm_tokens = new_tokens
            self._bm_sel_token = None
            self._mk_battle_map()

        def _battle_cast(self):
            """Cast gjeldende PNG til TV (cache-bust med query-streng)."""
            if not CAST_AVAILABLE or not self.cast.mc:
                self._battle_update_info(
                    "Ingen Cast-enhet tilkoblet. "
                    "Gaa til Cast-fanen.")
                return
            # Sikre at PNG er oppdatert
            self._battle_render()
            self._bm_cast_counter += 1
            url = self.server.url(BATTLE_PNG)
            url = f"{url}?t={self._bm_cast_counter}"
            # Bruk PNG mime
            def _c():
                try:
                    self.cast.mc.play_media(url, 'image/png')
                    self.cast.mc.block_until_active()
                    Clock.schedule_once(
                        lambda dt: self._battle_update_info(
                            "Sendt til TV."), 0)
                except Exception as e:
                    log(f"Cast battlemap error: {e}")
                    Clock.schedule_once(
                        lambda dt: self._battle_update_info(
                            "Cast feilet."), 0)
            threading.Thread(target=_c, daemon=True).start()

        def _battle_pick_bg(self):
            """Vis bildevalg fra MAPS_DIR."""
            self.tool_area.clear_widgets()
            p = BoxLayout(orientation='vertical',
                          spacing=dp(6), padding=dp(6))

            top = BoxLayout(size_hint_y=None, height=dp(42),
                            spacing=dp(6))
            top.add_widget(mkbtn("Tilbake",
                                 self._battle_show_menu,
                                 small=True, size_hint_x=0.3))
            top.add_widget(mklbl(f"Velg kart ({MAPS_DIR})",
                                 color=GOLD, size=11, bold=True))
            p.add_widget(top)

            p.add_widget(mklbl(
                "Legg kartbilder i /sdcard/Documents/"
                "CampaignForge/maps/",
                color=DIM, size=9, h=18))

            scroll = ScrollView()
            g = GridLayout(cols=2, spacing=dp(6), padding=dp(4),
                           size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))

            try:
                files = sorted([
                    f for f in os.listdir(MAPS_DIR)
                    if f.lower().endswith(IMG_EXT)])
            except Exception:
                files = []

            if not files:
                g.add_widget(mklbl(
                    "Ingen kart funnet.\n"
                    "Legg .png/.jpg i maps-mappen.",
                    color=DIM, size=11, h=60))
            else:
                for fn in files:
                    path = os.path.join(MAPS_DIR, fn)
                    b = mkbtn(
                        fn,
                        lambda p=path: self._battle_set_bg(p),
                        small=True)
                    b.size_hint_y = None
                    b.height = dp(44)
                    g.add_widget(b)

            scroll.add_widget(g)
            p.add_widget(scroll)
            self.tool_area.add_widget(p)

        def _battle_set_bg(self, path):
            self._bm_bg = path
            self._battle_show_menu()


        def on_stop(self):
            self.player.stop()
            self.streamer.stop()
            # Stopp alle scenario-lag
            for lp in getattr(self, '_scn_layers', []):
                if lp:
                    try: lp.stop()
                    except: pass
            # Stopp one-shots
            try: self.oneshot.stop_all()
            except: pass
            self.server.stop()
            self.cast.disconnect()
            save_json(CHAR_FILE, self.chars)
            save_json(SCENARIO_FILE, self.scenarios)
            # Lagre battlemap hvis initialisert
            if hasattr(self, '_bm_init_done'):
                self._battle_save()

    log("Starting app...")
    CampaignForgeApp().run()

except Exception as e:
    log(f"CRASH: {e}")
    log(traceback.format_exc())
