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
from kivy.properties import ListProperty, NumericProperty
from kivy.lang import Builder

# === LOGG ===
LOG = "/sdcard/Documents/CampaignForge/crash.log"
try:
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
except Exception:
    pass

def log(msg):
    try:
        with open(LOG, "a") as f:
            f.write(msg + "\n")
    except Exception:
        pass

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

# === STIER ===
BASE_DIR    = "/sdcard/Documents/CampaignForge"
IMG_DIR     = os.path.join(BASE_DIR, "images")
MUSIC_DIR   = os.path.join(BASE_DIR, "music")
ONESHOT_DIR = os.path.join(BASE_DIR, "oneshots")
MAPS_DIR    = os.path.join(BASE_DIR, "maps")
CHAR_FILE     = os.path.join(BASE_DIR, "characters.json")
SCENARIO_FILE = os.path.join(BASE_DIR, "scenarios.json")
LIBRARY_FILE  = os.path.join(BASE_DIR, "library.json")
BATTLE_FILE = os.path.join(BASE_DIR, "battlemap.json")
BATTLE_PNG  = os.path.join(BASE_DIR, "battlemap_current.png")

# Bakgrunnsbilde – bundlet ved siden av main.py i APK-en, eller
# overstyrt med en fil i Documents/CampaignForge/.
APP_DIR = os.path.dirname(os.path.abspath(__file__)) \
    if "__file__" in globals() else os.getcwd()
BG_IMAGE_BUNDLED  = os.path.join(APP_DIR, "background.png")
BG_IMAGE_OVERRIDE = os.path.join(BASE_DIR, "background.png")

# === FARGER – MOSSY GROVE ===
BG   = [0.05, 0.08, 0.06, 1]
BG2  = [0.09, 0.13, 0.10, 0.82]   # lett translucent for bakgrunnsbilde
INPUT= [0.06, 0.09, 0.07, 1]
BTN  = [0.16, 0.24, 0.17, 1]
BTNH = [0.28, 0.42, 0.26, 1]
SHAD = [0.01, 0.02, 0.01, 0.75]
GOLD = [0.86, 0.74, 0.42, 1]
GDIM = [0.55, 0.48, 0.25, 1]
TXT  = [0.86, 0.88, 0.74, 1]
DIM  = [0.52, 0.58, 0.46, 1]
RED  = [0.78, 0.30, 0.22, 1]
GRN  = [0.45, 0.70, 0.38, 1]
BLUE = [0.36, 0.50, 0.68, 1]
BLK  = [0.0, 0.0, 0.0, 1]

# Scenario-bokser
LOOP_BG    = [0.16, 0.24, 0.17, 1]
LOOP_BG_ON = [0.28, 0.42, 0.26, 1]
ONE_BG     = [0.05, 0.10, 0.07, 1]
ONE_BORDER = [0.86, 0.74, 0.42, 1]

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
    for d in [IMG_DIR, MUSIC_DIR, ONESHOT_DIR, MAPS_DIR]:
        try:
            os.makedirs(d, exist_ok=True)
        except Exception as e:
            log(f"makedirs {d}: {e}")
    log(f"Dirs OK: img={os.path.exists(IMG_DIR)}, "
        f"mus={os.path.exists(MUSIC_DIR)}, one={os.path.exists(ONESHOT_DIR)}")

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
        Color:
            rgba: self.border_color
        Line:
            rounded_rectangle: (self.x + dp(1), self.y + dp(1), self.width - dp(2), self.height - dp(2), self.radius)
            width: 1.2

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
        Color:
            rgba: self.border_color
        Line:
            rounded_rectangle: (self.x + dp(1), self.y + dp(1), self.width - dp(2), self.height - dp(2), self.radius)
            width: self.border_width

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
    bg_color     = ListProperty(BTN)
    shadow_color = ListProperty(SHAD)
    border_color = ListProperty(GDIM)
    radius       = NumericProperty(dp(14))

class RToggle(ToggleButton):
    bg_color     = ListProperty(BTN)
    shadow_color = ListProperty(SHAD)
    border_color = ListProperty(GDIM)
    border_width = NumericProperty(1.2)
    radius       = NumericProperty(dp(14))

class RBox(BoxLayout):
    bg_color = ListProperty(BG2)
    radius   = NumericProperty(dp(8))

class FramedBox(BoxLayout):
    frame_color = ListProperty(GDIM)

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

def mkvol(callback, value=0.7):
    vr = BoxLayout(size_hint_y=None, height=dp(32), padding=[dp(10), 0])
    vr.add_widget(Label(text="Vol", color=DIM, size_hint_x=0.08, font_size=sp(10)))
    sl = Slider(min=0, max=1, value=value, size_hint_x=0.92)
    sl.bind(value=lambda s, v: callback(v))
    vr.add_widget(sl)
    return vr
