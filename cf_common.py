"""CampaignForge – delte konstanter, widgets og hjelpere.

Importert av main.py, scenarios.py og audio_layers.py.
Holder alt som flere moduler trenger på ett sted, så endring av f.eks.
en farge kan gjøres uten å redigere hovedfila.
"""
import os, json
from functools import partial

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
from kivy.utils import platform
from kivy.metrics import dp, sp
from kivy.properties import ListProperty, NumericProperty, BooleanProperty, ObjectProperty, StringProperty
from kivy.lang import Builder
from kivy.clock import Clock
from kivy.graphics.texture import Texture

# === STIER ===
# Android 13+ scoped storage gjør at appen IKKE kan opprette/skrive nye
# filer i /sdcard/Documents/... uten MANAGE_EXTERNAL_STORAGE.
# Skille:
#   USER_DIR  – brukerens mappe i Documents (kun for filer brukeren
#               legger inn selv via filbehandler – f.eks. kart, bilder,
#               musikk). Appen LESER herfra.
#   DATA_DIR  – appens private mappe (alltid skrivbar uten tillatelser).
#               Alle JSON-filer, generert PNG og logg legges hit.

if platform == 'android':
    # ANDROID_PRIVATE er satt av p4a; bruk det først.
    # På noen enheter er det /data/user/0/<pkg>/files, på andre
    # /data/data/<pkg>/files. realpath() løser symlinker så
    # alle senere stier matcher faktisk fysisk path (kritisk for
    # HTTP-serveren som bruker startswith/relpath på root).
    _raw_data = os.environ.get(
        'ANDROID_PRIVATE',
        '/data/data/org.rpg.campaignforge/files')
    try:
        DATA_DIR = os.path.realpath(_raw_data)
    except Exception:
        DATA_DIR = _raw_data
    USER_DIR = "/sdcard/Documents/CampaignForge"
else:
    # Desktop/testing: alt i hjemmemappen
    DATA_DIR = os.path.expanduser("~/.campaignforge")
    USER_DIR = DATA_DIR

# Sørg for at den private data-mappen finnes (skal alltid lykkes)
try:
    os.makedirs(DATA_DIR, exist_ok=True)
except Exception:
    pass

# Bruker-innhold (les-fra)
BASE_DIR    = USER_DIR     # bevart navn for kompatibilitet med eldre kode
IMG_DIR     = os.path.join(USER_DIR, "images")
MUSIC_DIR   = os.path.join(USER_DIR, "music")
ONESHOT_DIR = os.path.join(USER_DIR, "oneshots")
MAPS_DIR    = os.path.join(USER_DIR, "maps")

# App-skrevne filer (privat skrivbar mappe)
CHAR_FILE     = os.path.join(DATA_DIR, "characters.json")
SCENARIO_FILE = os.path.join(DATA_DIR, "scenarios.json")
LIBRARY_FILE  = os.path.join(DATA_DIR, "library.json")
BATTLE_FILE   = os.path.join(DATA_DIR, "battlemap.json")
BATTLE_PNG    = os.path.join(DATA_DIR, "battlemap_current.png")
BATTLE_BG_PNG = os.path.join(DATA_DIR, "battlemap_bg_current.png")

# === LOGG (i privat mappe – unngår permission-feil) ===
LOG = os.path.join(DATA_DIR, "crash.log")

def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

# === MIGRASJON FRA GAMMEL STI ===
def _migrate_legacy_files():
    """Flytt JSON-filer fra gammel /sdcard-sti til ny privat sti.
    Kjøres én gang ved oppstart. Hopper over hvis ny fil allerede finnes
    eller hvis lese-tilgangen til den gamle filen ikke er tilgjengelig."""
    if platform != 'android' or USER_DIR == DATA_DIR:
        return
    legacy_files = ("battlemap.json", "characters.json",
                    "scenarios.json", "library.json", "crash.log")
    for fn in legacy_files:
        src = os.path.join(USER_DIR, fn)
        dst = os.path.join(DATA_DIR, fn)
        if os.path.exists(src) and not os.path.exists(dst):
            try:
                with open(src, 'rb') as fs, open(dst, 'wb') as fd:
                    fd.write(fs.read())
                log(f"Migrert {fn}: {src} -> {dst}")
            except Exception as e:
                log(f"Migrasjon av {fn} feilet: {e}")

_migrate_legacy_files()

# === ANDROID MEDIAPLAYER (jnius) ===
USE_JNIUS = False
MediaPlayer = None
if platform == 'android':
    try:
        from jnius import autoclass
        MediaPlayer = autoclass('android.media.MediaPlayer')
        USE_JNIUS = True
        log("Using Android MediaPlayer")
    except Exception:
        pass

# Bakgrunnsbilde – bundlet ved siden av main.py i APK-en, eller
# overstyrt med en fil i Documents/CampaignForge/ (bruker kan legge
# inn egen bakgrunn).
APP_DIR = os.path.dirname(os.path.abspath(__file__)) \
    if "__file__" in globals() else os.getcwd()
BG_IMAGE_BUNDLED  = os.path.join(APP_DIR, "background.png")
BG_IMAGE_OVERRIDE = os.path.join(USER_DIR, "background.png")
# Trebakgrunn – legges UNDER background.png som heldekkende tekstur.
# Bundlet med APK-en. Brukeren kan også legge en alternativ
# dark-wood.png i Documents/CampaignForge/.
WOOD_BUNDLED  = os.path.join(APP_DIR, "dark-wood.png")
WOOD_OVERRIDE = os.path.join(USER_DIR, "dark-wood.png")

# === FARGER – ANCIENT TOME (mørk brun bakgrunn + grønne knapper + gull) ===
# Bakgrunner er brune (matcher splash). Knapper og faner er grønne
# (matcher emblemet og beholder den smaragd-aksenten Robin liker).
BG   = [0.07, 0.05, 0.04, 1]      # mørk svart-brun (hovedbakgrunn)
BG2  = [0.13, 0.09, 0.06, 0.55]   # mørk brun, mer translucent (lar tre/emblem skinne gjennom)
INPUT= [0.10, 0.07, 0.05, 1]      # tekstfelt-bakgrunn, mørk brun
BTN  = [0.16, 0.24, 0.17, 1]      # mosegroenn (knapper, idle) — som foer
BTNH = [0.28, 0.42, 0.26, 1]      # lysere groenn (knapper, aktiv) — som foer
SHAD = [0.0, 0.0, 0.0, 0.40]      # ren svart-skygge (mer kontrast paa brun)
GOLD = [0.86, 0.74, 0.42, 1]      # antikk gull (overskrifter, aktive)
GDIM = [0.55, 0.42, 0.22, 0.70]   # dempet brun-gull; for sub-overskrifter
GBORDER = [0.86, 0.74, 0.42, 1]   # solid gull for knapper og faner
GBORDER_DARK   = [0.40, 0.26, 0.06, 0.90]  # mørk amber ytre skygge-ring
GBORDER_BRIGHT = [1.0,  0.88, 0.42, 1.0]   # skinnende hoved-gull
GBORDER_GLINT  = [1.0,  0.97, 0.78, 0.55]  # hvit metal-glint innerst
TXT  = [0.92, 0.86, 0.72, 1]      # varm beige (kropps-tekst)
DIM  = [0.62, 0.54, 0.42, 1]      # dempet beige (sekundaer-tekst)
RED  = [0.82, 0.32, 0.22, 1]      # varm roed (advarsel/skade)
GRN  = [0.55, 0.70, 0.38, 1]      # demping av groennt — beholder for PC-token
BLUE = [0.42, 0.55, 0.72, 1]      # dempet blaa for info
BLK  = [0.0, 0.0, 0.0, 1]

# Indre kanter for "graverte" knapper (lys topp, mørk bunn)
INNER_HI = [1.0, 1.0, 0.9, 0.18]   # subtil lys-rim øverst
INNER_LO = [0.0, 0.0, 0.0, 0.30]   # subtil mørk-rim nederst

# Scenario-bokser
LOOP_BG    = [0.16, 0.24, 0.17, 1]      # mosegroenn (samme som BTN)
LOOP_BG_ON = [0.28, 0.42, 0.26, 1]      # lysere groenn (samme som BTNH)
ONE_BG     = [0.10, 0.07, 0.05, 1]      # mørk brun (matcher INPUT)
ONE_BORDER = [0.55, 0.42, 0.22, 0.80]   # dempet gull-brune tone


# === GRADIENT-TEKSTUR-HELPERE ===
# Kivy har ingen innebygd gradient-primitiv, men Texture-objekter kan
# fylles med vilkårlig pixel-data og rendres som vanlige Rectangle-
# teksturer. Det gir oss ekte glatte gradienter.

def make_horiz_gradient_tex(rgb, width=128, peak_alpha=0.95):
    """Lag en 1-rad-tekstur som fader fra alpha=0 (kant) → peak (senter) → 0 (kant).

    rgb: liste/tuple av 3 floats (0-1) for fargen
    width: antall horisontale piksler – høyere = jevnere
    peak_alpha: maksimal alpha i senter (0-1)

    Returnerer et Texture-objekt klar til bruk i Rectangle(texture=...).
    """
    tex = Texture.create(size=(width, 1), colorfmt='rgba')
    tex.mag_filter = 'linear'
    tex.min_filter = 'linear'
    r = int(rgb[0] * 255)
    g = int(rgb[1] * 255)
    b = int(rgb[2] * 255)
    buf = bytearray(width * 4)
    half = width / 2.0
    for x in range(width):
        # Cosinus-falloff gir mykere bell-kurve enn lineær
        # Avstand fra senter, normalisert 0..1
        d = abs(x - half) / half
        # Cosinus: alpha = peak * cos²(π/2 * d)
        # Det gir 1.0 i senter, 0.0 i kant, og helt smooth derivasjon
        import math
        a = peak_alpha * (math.cos(d * math.pi / 2) ** 2)
        idx = x * 4
        buf[idx] = r
        buf[idx + 1] = g
        buf[idx + 2] = b
        buf[idx + 3] = int(a * 255)
    tex.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
    return tex


def make_vert_gradient_tex(rgb_top, rgb_bot, height=128):
    """Lag en 1-kolonne-tekstur som fader vertikalt mellom to RGB-farger.

    Brukbar for å gi knapper en svak vertikal gradient (lyst i topp,
    mørkere mot bunn) for et "konvekst metall"-utseende.
    """
    tex = Texture.create(size=(1, height), colorfmt='rgba')
    tex.mag_filter = 'linear'
    tex.min_filter = 'linear'
    buf = bytearray(height * 4)
    for y in range(height):
        t = y / max(1, height - 1)  # 0 = bunn (kommer først i pixel-data)
        r = int((rgb_top[0] * t + rgb_bot[0] * (1 - t)) * 255)
        g = int((rgb_top[1] * t + rgb_bot[1] * (1 - t)) * 255)
        b = int((rgb_top[2] * t + rgb_bot[2] * (1 - t)) * 255)
        a = int((rgb_top[3] * t + rgb_bot[3] * (1 - t)) * 255) \
            if len(rgb_top) > 3 else 255
        idx = y * 4
        buf[idx] = r
        buf[idx + 1] = g
        buf[idx + 2] = b
        buf[idx + 3] = a
    tex.blit_buffer(bytes(buf), colorfmt='rgba', bufferfmt='ubyte')
    return tex


# Lazy-init: lages én gang ved første bruk og caches
_GRADIENT_CACHE = {}

def get_gold_glow_tex():
    """Hent (eller lag) cached gull-glød-tekstur for aktiv-fane-stripen."""
    key = 'gold_glow'
    if key not in _GRADIENT_CACHE:
        _GRADIENT_CACHE[key] = make_horiz_gradient_tex(
            (GOLD[0], GOLD[1], GOLD[2]), width=256, peak_alpha=0.95)
    return _GRADIENT_CACHE[key]

def get_tab_active_bg_tex():
    """Vertikal gradient for AKTIV faneknapp-bakgrunn.

    Lysere lauvgrønn øverst, dempet skogsgrønn nederst.
    Gir 'konvekst metall'-følelse.
    """
    key = 'tab_active_bg'
    if key not in _GRADIENT_CACHE:
        # Topp = lysere variant av BTNH, bunn = mørkere variant
        top = (BTNH[0] * 1.18, BTNH[1] * 1.18, BTNH[2] * 1.18, 1.0)
        bot = (BTNH[0] * 0.78, BTNH[1] * 0.78, BTNH[2] * 0.78, 1.0)
        # Begrens til [0,1]
        top = (min(1, top[0]), min(1, top[1]), min(1, top[2]), 1.0)
        _GRADIENT_CACHE[key] = make_vert_gradient_tex(top, bot, height=128)
    return _GRADIENT_CACHE[key]

def get_tab_inactive_bg_tex():
    """Vertikal gradient for INAKTIV faneknapp-bakgrunn."""
    key = 'tab_inactive_bg'
    if key not in _GRADIENT_CACHE:
        top = (BTN[0] * 1.25, BTN[1] * 1.25, BTN[2] * 1.25, 1.0)
        bot = (BTN[0] * 0.72, BTN[1] * 0.72, BTN[2] * 0.72, 1.0)
        top = (min(1, top[0]), min(1, top[1]), min(1, top[2]), 1.0)
        _GRADIENT_CACHE[key] = make_vert_gradient_tex(top, bot, height=128)
    return _GRADIENT_CACHE[key]


def get_button_bg_tex(base_rgba, pressed=False):
    """Vertikal gradient for knapper, bygget fra valgt basefarge."""
    rgb = tuple(round(c, 4) for c in base_rgba[:3])
    alpha = base_rgba[3] if len(base_rgba) > 3 else 1.0
    key = ('btn_bg', rgb, round(alpha, 4), pressed)
    if key not in _GRADIENT_CACHE:
        lift = 1.10 if pressed else 1.25
        sink = 0.62 if pressed else 0.72
        top = tuple(min(1.0, c * lift) for c in rgb) + (alpha,)
        bot = tuple(min(1.0, c * sink) for c in rgb) + (alpha,)
        _GRADIENT_CACHE[key] = make_vert_gradient_tex(top, bot, height=128)
    return _GRADIENT_CACHE[key]

def get_drop_shadow_tex():
    """Vertikal gradient for drop-shadow under knapper.

    Sterkest mørke alpha øverst (nærmest knappen), fader ut nedover.
    Brukes som tekstur på en RoundedRectangle plassert UNDER knappen,
    forskjøvet litt ned-til-høyre.
    """
    key = 'drop_shadow'
    if key not in _GRADIENT_CACHE:
        # I make_vert_gradient_tex er y=0 nederste pixel, y=height-1 øverste.
        # rgb_top brukes når t=1 (toppen, nær knappen)
        # rgb_bot brukes når t=0 (bunnen, lengst fra knappen)
        # Vi vil HA mørkest alpha nær knappen (toppen).
        top = (0, 0, 0, 0.55)   # sterk skygge nær knappen
        bot = (0, 0, 0, 0.05)   # nesten transparent nederst
        _GRADIENT_CACHE[key] = make_vert_gradient_tex(top, bot, height=128)
    return _GRADIENT_CACHE[key]


# === FILTYPER ===
IMG_EXT = ('.png', '.jpg', '.jpeg', '.webp')
SND_EXT = ('.mp3', '.ogg', '.wav', '.flac', '.m4a', '.aac')
HTTP_PORT = 8089

# === AMBIENT-LYDER (URL-strømmer) ===
AMBIENT_SOUNDS = [
    {"name": "— Natur —"},
    {"name": "Skog (fugler)", "url": "https://archive.org/download/forest-sounds-in-the-jura-mountains/Forest%20Sounds%20In%20The%20Jura%20Mountains.mp3"},
    {"name": "Regn",          "url": "https://archive.org/download/rain-sounds_202105/Rain%20Sounds.mp3"},
    {"name": "Tordenvær",     "url": "https://archive.org/download/thunderstorm-sounds/Thunderstorm%20Sounds.mp3"},
    {"name": "Bekk",          "url": "https://archive.org/download/stream-sounds/Stream%20Sounds.mp3"},
    {"name": "Bølger",        "url": "https://archive.org/download/ocean-sounds_202105/Ocean%20Sounds.mp3"},
    {"name": "Vind",          "url": "https://archive.org/download/wind-sounds/Wind%20Sounds.mp3"},
    {"name": "— Steder —"},
    {"name": "Tavern",        "url": "https://archive.org/download/tavern-ambience/Tavern%20Ambience.mp3"},
    {"name": "Marked",        "url": "https://archive.org/download/medieval-market/Medieval%20Market.mp3"},
    {"name": "Smie",          "url": "https://archive.org/download/blacksmith-sounds/Blacksmith%20Sounds.mp3"},
    {"name": "Slagmark",      "url": "https://archive.org/download/battlefield-sounds/Battlefield%20Sounds.mp3"},
    {"name": "— Stemning —"},
    {"name": "Mørk hule",     "url": "https://archive.org/download/cave-ambience/Cave%20Ambience.mp3"},
    {"name": "Krypt",         "url": "https://archive.org/download/crypt-ambience/Crypt%20Ambience.mp3"},
    {"name": "Horrorlyder",   "url": "https://archive.org/download/creepy-music-sounds/Horror%20Sound%20Effects.mp3"},
]

# === HERO'S JOURNEY (Vogler 12 steg) ===
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

# === MAPPER (kalles etter at tillatelser er gitt) ===
def ensure_dirs():
    # Privat data-mappe – skal alltid lykkes på Android
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except Exception as e:
        log(f"makedirs DATA_DIR {DATA_DIR}: {e}")
    # Brukerens mapper – kan feile på Android 13+ uten manuell oppretting,
    # men vi prøver siden noen enheter / tillatelser tillater det
    for d in [IMG_DIR, MUSIC_DIR, ONESHOT_DIR, MAPS_DIR]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            log(f"makedirs {d}: {e}")
    log(f"Dirs OK: data={os.path.exists(DATA_DIR)}, "
        f"img={os.path.exists(IMG_DIR)}, "
        f"mus={os.path.exists(MUSIC_DIR)}, "
        f"one={os.path.exists(ONESHOT_DIR)}, "
        f"maps={os.path.exists(MAPS_DIR)}")

# === JSON ===
def load_json(p, d=None):
    try:
        with open(p, 'r') as f:
            return json.load(f)
    except Exception:
        return d if d is not None else []

def save_json(p, d):
    try:
        with open(p, 'w') as f:
            json.dump(d, f, indent=2, ensure_ascii=False)
    except Exception as e:
        log(f"save_json {p}: {e}")

# === STILEDE WIDGETS ===
# KV-regler bygger opp en lagdelt visuell stack for hver knapp:
#   1. Tre forskjøvede skygge-rektangler (svakeste først, sterkeste sist)
#      som simulerer myk blur. Forskyves skrått ned-til-høyre.
#   2. Bakgrunnsfyll (bg_color) i avrundet rektangel.
#   3. Indre lys-rim øverst og indre skygge-rim nederst – gir et
#      "gravert i metall"-utseende.
#   4. Tykkere gull-ramme på utsiden.
Builder.load_string('''
<RBtn>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    canvas.before:
        # --- Myk skygge med ekte gradient-tekstur ---
        # Plasseres BAK knappen, forskjøvet skrått ned-til-høyre.
        # Teksturen har sterkere alpha øverst (nær knappen) og fader
        # ut nedover. Når knappen trykkes, "synker" skyggen og dempes.
        Color:
            rgba: 1, 1, 1, 0.30 if self._pressed else 1.0
        RoundedRectangle:
            texture: self.shadow_tex
            pos: self.x + (dp(1) if self._pressed else dp(3)), self.y - (dp(2) if self._pressed else dp(5))
            size: self.width, self.height
            radius: [self.radius + dp(2)]
        # --- Bakgrunnsfyll (mørkere når trykket) ---
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            texture: self.bg_tex_pressed if self._pressed else self.bg_tex_normal
            pos: self.pos
            size: self.size
            radius: [self.radius]
        # --- Indre lys-rim på øvre kant (subtilt highlight) ---
        Color:
            rgba: 1, 1, 0.9, 0.10 if self._pressed else 0.18
        Line:
            rounded_rectangle: (self.x + dp(2), self.y + dp(2), self.width - dp(4), self.height - dp(4), self.radius - dp(1))
            width: 1.0
        # --- Indre mørk-rim på nedre kant (subtil dybde) ---
        Color:
            rgba: 0, 0, 0, 0.30
        Line:
            points: self.x + dp(4), self.y + dp(2), self.x + self.width - dp(4), self.y + dp(2)
            width: 1.0
        # --- Ytre mørk amber-ring (dybde/skygge) ---
        Color:
            rgba: self.border_dark_color
        Line:
            rounded_rectangle: (self.x - dp(1), self.y - dp(1), self.width + dp(2), self.height + dp(2), self.radius + dp(1))
            width: 2.0
        # --- Hoved gull-ring (metallisk glans) ---
        Color:
            rgba: self.border_color
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, self.radius)
            width: self.border_width
        # --- Indre glint-ring (hvit metallic highlight) ---
        Color:
            rgba: self.border_glint_color
        Line:
            rounded_rectangle: (self.x + dp(1.5), self.y + dp(1.5), self.width - dp(3), self.height - dp(3), self.radius - dp(1))
            width: 1.0

<RToggle>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    canvas.before:
        # --- Myk skygge (3 lag stablet) ---
        # Når toggle er 'down' (aktiv) skal den se "trykket" ut konstant.
        # Bruker samme gradient-tekstur som RBtn for konsistens.
        Color:
            rgba: 1, 1, 1, 0.30 if self.state == 'down' else 1.0
        RoundedRectangle:
            texture: self.shadow_tex
            pos: self.x + (dp(1) if self.state == 'down' else dp(3)), self.y - (dp(2) if self.state == 'down' else dp(5))
            size: self.width, self.height
            radius: [self.radius + dp(2)]
        # --- Bakgrunnsfyll (mørkere når aktiv) ---
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            texture: self.bg_tex_active if self.state == 'down' else self.bg_tex_normal
            pos: self.pos
            size: self.size
            radius: [self.radius]
        # --- Indre lys-rim på øvre kant ---
        Color:
            rgba: 1, 1, 0.9, 0.10 if self.state == 'down' else 0.18
        Line:
            rounded_rectangle: (self.x + dp(2), self.y + dp(2), self.width - dp(4), self.height - dp(4), self.radius - dp(1))
            width: 1.0
        # --- Indre mørk-rim på nedre kant ---
        Color:
            rgba: 0, 0, 0, 0.30
        Line:
            points: self.x + dp(4), self.y + dp(2), self.x + self.width - dp(4), self.y + dp(2)
            width: 1.0
        # --- Ytre mørk amber-ring (dybde/skygge) ---
        Color:
            rgba: self.border_dark_color
        Line:
            rounded_rectangle: (self.x - dp(1), self.y - dp(1), self.width + dp(2), self.height + dp(2), self.radius + dp(1))
            width: 2.0
        # --- Hoved gull-ring (metallisk glans) ---
        Color:
            rgba: self.border_color
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, self.radius)
            width: self.border_width
        # --- Indre glint-ring (hvit metallic highlight) ---
        Color:
            rgba: self.border_glint_color
        Line:
            rounded_rectangle: (self.x + dp(1.5), self.y + dp(1.5), self.width - dp(3), self.height - dp(3), self.radius - dp(1))
            width: 1.0

<RTab>:
    background_normal: ''
    background_down: ''
    background_color: 0, 0, 0, 0
    bold: True
    canvas.before:
        # Skygge under fanen med gradient-tekstur (samme tekstur som RBtn).
        # Mer alpha + større offset når aktiv for å gi følelse av at fanen
        # løftes opp fra tab-baren.
        Color:
            rgba: 1, 1, 1, 1.0 if self.state == 'down' else 0.55
        RoundedRectangle:
            texture: self.shadow_tex
            pos: self.x + dp(2), self.y - dp(3) if self.state == 'down' else self.y - dp(2)
            size: self.width, self.height
            radius: [self.radius + dp(1)]
        # Bakgrunnsfyll – ekte vertikal gradient (lysere topp, mørkere bunn).
        # Velger riktig tekstur basert på aktiv-tilstand (cached i memory).
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            texture: self.bg_tex_active if self.state == 'down' else self.bg_tex_inactive
            pos: self.pos
            size: self.size
            radius: [self.radius]
        # Indre lys-highlight bare når aktiv
        Color:
            rgba: 1, 1, 0.85, 0.12 if self.state == 'down' else 0
        Line:
            rounded_rectangle: (self.x + dp(2), self.y + dp(2), self.width - dp(4), self.height - dp(4), self.radius - dp(1))
            width: 1.0
        # --- Ytre mørk amber-ring (dybde/skygge) ---
        Color:
            rgba: self.border_dark_color
        Line:
            rounded_rectangle: (self.x - dp(1), self.y - dp(1), self.width + dp(2), self.height + dp(2), self.radius + dp(1))
            width: 2.0
        # --- Hoved gull-ring (metallisk glans) ---
        Color:
            rgba: self.border_color
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, self.radius)
            width: self.border_width
        # --- Indre glint-ring (hvit metallic highlight) ---
        Color:
            rgba: self.border_glint_color
        Line:
            rounded_rectangle: (self.x + dp(1.5), self.y + dp(1.5), self.width - dp(3), self.height - dp(3), self.radius - dp(1))
            width: 1.0
        # AKTIV-INDIKATOR: ekte glatt cosinus-gradient via tekstur.
        # Stripa er 3px høy, går nesten helt ut til kantene.
        # Teksturen er en horisontal gull-glød som peaker i senter.
        # Når state ikke er 'down', tegner vi størrelse 0 (usynlig).
        Color:
            rgba: 1, 1, 1, 1 if self.state == 'down' else 0
        Rectangle:
            texture: self.glow_tex
            pos: self.x + dp(4), self.y + dp(3)
            size: (self.width - dp(8)) if self.state == 'down' else 0, dp(3)

<RBox>:
    canvas.before:
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]

<WoodPanel>:
    canvas.before:
        # Fallback-fyll under teksturen (brun, så det ser riktig ut
        # selv hvis dark-wood.png ikke finnes på enheten)
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]
        # Tre-tekstur fra dark-wood.png – dekker hele panelet.
        # tex_coords forskyver teksturen vannrett basert på
        # tex_offset_x (0.0–1.0). Verdier > 0 "ruller" teksturen
        # sideveis så plankene står på andre steder enn bakgrunnen.
        Color:
            rgba: 1, 1, 1, 1
        RoundedRectangle:
            source: self.wood_source if self.wood_source else ''
            pos: self.pos
            size: self.size
            radius: [self.radius]
            tex_coords: (self.tex_offset_x, 0, 1 + self.tex_offset_x, 0, 1 + self.tex_offset_x, 1, self.tex_offset_x, 1)
        # Tint over teksturen — kan være mørklegging eller lysning.
        Color:
            rgba: self.tint_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]
        # --- Ytre mørk amber-ring (dybde/skygge) ---
        Color:
            rgba: self.border_dark_color
        Line:
            rounded_rectangle: (self.x - dp(1), self.y - dp(1), self.width + dp(2), self.height + dp(2), self.radius + dp(1))
            width: 2.0
        # --- Hoved gull-ring (metallisk glans) ---
        Color:
            rgba: self.border_color
        Line:
            rounded_rectangle: (self.x, self.y, self.width, self.height, self.radius)
            width: self.border_width
        # --- Indre glint-ring (hvit metallic highlight) ---
        Color:
            rgba: self.border_glint_color
        Line:
            rounded_rectangle: (self.x + dp(1.5), self.y + dp(1.5), self.width - dp(3), self.height - dp(3), self.radius - dp(1))
            width: max(1.0, self.border_width * 0.5)

<PreviewFrame>:
    canvas.before:
        Color:
            rgba: self.shadow_color
        RoundedRectangle:
            pos: self.x + dp(3), self.y - dp(4)
            size: self.width, self.height
            radius: [self.radius + dp(2)]
        Color:
            rgba: self.bg_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]
        Color:
            rgba: self.glow_color if self.has_content else (0, 0, 0, 0)
        RoundedRectangle:
            pos: self.x + dp(14), self.top - dp(12)
            size: self.width - dp(28), dp(4)
            radius: [dp(2)]
        Color:
            rgba: self.inner_frame_color
        Line:
            rounded_rectangle: (self.x + dp(4), self.y + dp(4), self.width - dp(8), self.height - dp(8), self.radius - dp(3))
            width: 1.1
        Color:
            rgba: self.frame_color
        Line:
            rounded_rectangle: (self.x + dp(1.5), self.y + dp(1.5), self.width - dp(3), self.height - dp(3), self.radius - dp(1))
            width: 2.0
        Color:
            rgba: self.highlight_color
        Line:
            rounded_rectangle: (self.x + dp(7), self.y + dp(7), self.width - dp(14), self.height - dp(14), self.radius - dp(6))
            width: 0.9

<FramedBox>:
    canvas.before:
        # Dobbel ramme for premium-utseende:
        # ytre svak skygge, indre dempet brun-gull
        Color:
            rgba: 0, 0, 0, 0.30
        Line:
            rectangle: (self.x - dp(1), self.y - dp(1), self.width + dp(2), self.height + dp(2))
            width: 1.0
        Color:
            rgba: self.frame_color
        Line:
            rectangle: (self.x, self.y, self.width, self.height)
            width: 3.0
''')

class RBtn(Button):
    bg_color     = ListProperty(BTN)
    shadow_color = ListProperty(SHAD)
    border_color = ListProperty(GBORDER_BRIGHT)
    border_dark_color = ListProperty(GBORDER_DARK)
    border_glint_color = ListProperty(GBORDER_GLINT)
    border_width = NumericProperty(2.5)
    radius       = NumericProperty(dp(14))
    _pressed     = BooleanProperty(False)
    shadow_tex   = ObjectProperty(None, allownone=True)
    bg_tex_normal = ObjectProperty(None, allownone=True)
    bg_tex_pressed = ObjectProperty(None, allownone=True)

    def __init__(self, **kw):
        super().__init__(**kw)
        self.shadow_tex = get_drop_shadow_tex()
        self._refresh_bg_textures()

    def _refresh_bg_textures(self):
        self.bg_tex_normal = get_button_bg_tex(self.bg_color, pressed=False)
        self.bg_tex_pressed = get_button_bg_tex(self.bg_color, pressed=True)

    def on_bg_color(self, *_):
        self._refresh_bg_textures()

    def on_press(self):
        self._pressed = True

    def on_release(self):
        self._pressed = False

    def on_touch_up(self, touch):
        # Sikre at _pressed alltid resettes selv om touch slippes utenfor
        self._pressed = False
        return super().on_touch_up(touch)

class RToggle(ToggleButton):
    bg_color     = ListProperty(BTN)
    shadow_color = ListProperty(SHAD)
    border_color = ListProperty(GBORDER_BRIGHT)
    border_dark_color = ListProperty(GBORDER_DARK)
    border_glint_color = ListProperty(GBORDER_GLINT)
    border_width = NumericProperty(2.5)
    radius       = NumericProperty(dp(14))
    active_bg_color = ListProperty(BTNH)
    inactive_bg_color = ListProperty(BTN)
    active_text_color = ListProperty(GOLD)
    inactive_text_color = ListProperty(DIM)
    shadow_tex   = ObjectProperty(None, allownone=True)
    bg_tex_normal = ObjectProperty(None, allownone=True)
    bg_tex_active = ObjectProperty(None, allownone=True)

    @staticmethod
    def _as_color_list(value):
        if value is None or isinstance(value, (str, bytes)):
            return None
        try:
            return list(value)
        except TypeError:
            return None

    def __init__(self, **kw):
        self._style_ready = False
        self._initial_state = 'down' if kw.get('state') == 'down' else 'normal'
        self._initial_bg_color = self._as_color_list(kw.get('bg_color')) if 'bg_color' in kw else None
        self._initial_text_color = self._as_color_list(kw.get('color')) if 'color' in kw else None
        self._has_active_bg_color = 'active_bg_color' in kw
        self._has_inactive_bg_color = 'inactive_bg_color' in kw
        self._has_active_text_color = 'active_text_color' in kw
        self._has_inactive_text_color = 'inactive_text_color' in kw
        super().__init__(**kw)
        self.shadow_tex = get_drop_shadow_tex()
        self._refresh_bg_textures()
        Clock.schedule_once(self._finish_style_init, 0)

    def _refresh_bg_textures(self):
        self.bg_tex_normal = get_button_bg_tex(self.bg_color, pressed=False)
        self.bg_tex_active = get_button_bg_tex(self.bg_color, pressed=True)

    def on_bg_color(self, *_):
        self._refresh_bg_textures()

    def on_state(self, *_):
        if self._style_ready:
            self._sync_state_style()

    def _finish_style_init(self, *_):
        if self._initial_bg_color is not None:
            if self._initial_state == 'down' and not self._has_active_bg_color:
                self.active_bg_color = self._initial_bg_color
            elif self._initial_state == 'normal' and not self._has_inactive_bg_color:
                self.inactive_bg_color = self._initial_bg_color
        if self._initial_text_color is not None:
            if self._initial_state == 'down' and not self._has_active_text_color:
                self.active_text_color = self._initial_text_color
            elif self._initial_state == 'normal' and not self._has_inactive_text_color:
                self.inactive_text_color = self._initial_text_color
        self._style_ready = True
        self._sync_state_style()

    def _sync_state_style(self):
        active = self.state == 'down'
        self.bg_color = self.active_bg_color if active else self.inactive_bg_color
        self.color = self.active_text_color if active else self.inactive_text_color

class RTab(ToggleButton):
    """Toggle-knapp for fane-bar – ekte gradient på bakgrunn og aktiv-stripe.

    Bruker fire teksturer (alle cached globalt):
    - bg_tex_inactive: vertikal grønn gradient for inaktiv tilstand
    - bg_tex_active: lysere vertikal grønn gradient når aktiv
    - shadow_tex: vertikal mørk gradient for skygge under fanen
    - glow_tex: horisontal cosinus-glød for gull-stripa i bunnen

    Dette gir ekte glatte gradienter uten synlige trinn.
    """
    bg_color          = ListProperty(BTN)         # ikke brukt for fyll, men
                                                  # bevart for kompatibilitet
    border_color      = ListProperty(GBORDER)
    border_dark_color = ListProperty(GBORDER_DARK)
    border_glint_color = ListProperty(GBORDER_GLINT)
    border_width      = NumericProperty(2.5)
    indicator_color   = ListProperty(GOLD)
    radius            = NumericProperty(dp(10))
    glow_tex          = ObjectProperty(None, allownone=True)
    bg_tex_active     = ObjectProperty(None, allownone=True)
    bg_tex_inactive   = ObjectProperty(None, allownone=True)
    shadow_tex        = ObjectProperty(None, allownone=True)

    def __init__(self, **kw):
        super().__init__(**kw)
        # Hent cached teksturer ved opprettelse
        self.glow_tex = get_gold_glow_tex()
        self.bg_tex_active = get_tab_active_bg_tex()
        self.bg_tex_inactive = get_tab_inactive_bg_tex()
        self.shadow_tex = get_drop_shadow_tex()

class RBox(BoxLayout):
    bg_color = ListProperty(BG2)
    radius   = NumericProperty(dp(8))

class WoodPanel(BoxLayout):
    """Container med dark-wood.png-tekstur og gull-kant.

    Bruker den bundlede dark-wood.png som faktisk tre-tekstur
    (matcher splash) — krever at `wood_source` settes før widgeten
    bygges. Hvis kilden ikke finnes, faller den tilbake til ren
    brun fyll.

    `tint_color` legges over teksturen som overlay. Default er en
    svak mørklegging slik at panelet skiller seg subtilt fra
    bakgrunnen. Kan også settes til positiv (hvit) alpha for å
    lysne — for eksempel når et panel skal være tydelig lysere
    enn omgivelsene (som minigalleriet i Bilder-fanen).

    `tex_offset_x` (0.0–1.0) forskyver tre-teksturen vannrett slik
    at panelet ikke flukter med bakgrunnen som har samme bilde."""
    border_color = ListProperty(GBORDER)
    border_dark_color = ListProperty(GBORDER_DARK)
    border_glint_color = ListProperty(GBORDER_GLINT)
    border_width = NumericProperty(2.0)
    radius       = NumericProperty(dp(12))
    wood_source  = StringProperty(WOOD_BUNDLED if os.path.exists(WOOD_BUNDLED) else "")
    bg_color     = ListProperty([0.16, 0.11, 0.07, 0.95])
    tint_color   = ListProperty([0.0, 0.0, 0.0, 0.30])
    dim_color    = ListProperty([0.0, 0.0, 0.0, 0.30])
    tex_offset_x = NumericProperty(0.0)
    shadow_color = ListProperty(SHAD)

    def __init__(self, **kw):
        super().__init__(**kw)
        # Sett tekstur til wrap=repeat slik at tex_coords > 1.0 ruller
        # over og bildet repeteres i stedet for å klippe. Må gjøres
        # etter at canvas er bygget. schedule_once for å unngå race
        # med kv-instanseringen.
        Clock.schedule_once(self._enable_tex_wrap, 0)
        self.bind(wood_source=lambda *a:
                  Clock.schedule_once(self._enable_tex_wrap, 0))

    def _enable_tex_wrap(self, *a):
        try:
            # Finn RoundedRectangle med teksturen i canvas.before.
            # Den andre RoundedRectangle (etter fallback-fyllet) er
            # tekstur-rektangelet.
            from kivy.graphics import RoundedRectangle as RR
            count = 0
            for instr in self.canvas.before.children:
                if isinstance(instr, RR) and instr.texture:
                    count += 1
                    if count == 2:
                        instr.texture.wrap = 'repeat'
                        break
        except Exception:
            pass

class PreviewFrame(BoxLayout):
    bg_color = ListProperty([0.02, 0.02, 0.02, 1])
    shadow_color = ListProperty([0.0, 0.0, 0.0, 0.34])
    frame_color = ListProperty([0.80, 0.68, 0.36, 0.95])
    inner_frame_color = ListProperty([0.36, 0.29, 0.16, 0.95])
    glow_color = ListProperty([0.86, 0.74, 0.42, 0.08])
    highlight_color = ListProperty([1.0, 0.96, 0.82, 0.09])
    has_content = BooleanProperty(False)
    radius = NumericProperty(dp(18))

class FramedBox(BoxLayout):
    frame_color = ListProperty(GDIM)


# === SKRIFT-HIERARKI ===
# Konsistente størrelser så hele appen leses likt.
FONT_H1   = 16   # store overskrifter (paneler, skjermer)
FONT_H2   = 13   # mellomstore overskrifter (sub-paneler)
FONT_BODY = 12   # brødtekst, knappetekst
FONT_SMALL = 11  # små knapper, sekundærtekst
FONT_DIM  = 10   # dempede labels, hint-tekst, tellere

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
        l.bind(width=lambda w, v: setattr(w, 'text_size', (v - dp(8), None)))
        l.bind(texture_size=l.setter('size'))
    return l

def mksep(h=6):
    return Widget(size_hint_y=None, height=dp(h))

def mkdiv(margin_y=4, alpha=0.25):
    """Subtil horisontal gull-linje som visuell seksjon-skiller.

    margin_y: vertikal padding over og under linjen (dp).
    alpha: gjennomsiktighet på gull-fargen (0-1).
    """
    wrap = BoxLayout(size_hint_y=None, height=dp(margin_y * 2 + 1),
                     padding=[dp(8), dp(margin_y)])
    line = Widget(size_hint_y=None, height=dp(1))
    from kivy.graphics import Color, Rectangle
    with line.canvas:
        Color(GOLD[0], GOLD[1], GOLD[2], alpha)
        rect = Rectangle(pos=line.pos, size=line.size)
    line.bind(pos=lambda w, v: setattr(rect, 'pos', w.pos),
              size=lambda w, v: setattr(rect, 'size', w.size))
    wrap.add_widget(line)
    return wrap

def mkvol(callback, value=0.7):
    vr = BoxLayout(size_hint_y=None, height=dp(32), padding=[dp(10), 0])
    vr.add_widget(Label(text="Vol", color=DIM, size_hint_x=0.08, font_size=sp(10)))
    sl = Slider(min=0, max=1, value=value, size_hint_x=0.92)
    sl.bind(value=lambda s, v: callback(v))
    vr.add_widget(sl)
    return vr
