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
        from PIL import (
            Image as PILImage,
            ImageDraw as PILDraw,
            ImageFont as PILFont,
            ImageOps as PILImageOps,
            ImageEnhance as PILImageEnhance,
        )
        # Pillow eksponerer LANCZOS ulikt mellom versjoner.
        PIL_LANCZOS_FALLBACK = 1
        PIL_LANCZOS = getattr(
            getattr(PILImage, 'Resampling', PILImage),
            'LANCZOS',
            getattr(PILImage, 'LANCZOS', PIL_LANCZOS_FALLBACK))
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
    # === IMPORTER FRA EGNE MODULER ===
    # All delt funksjonalitet ligger nå i cf_common.py.
    # LayerPlayer/OneShotPlayer i audio_layers.py.
    # Hele scenario-funksjonaliteten i scenarios.py.
    from cf_common import (
        log as _cf_log,  # cf_common har sin egen log; unngå navnekollisjon
        USE_JNIUS, MediaPlayer,
        BASE_DIR, DATA_DIR, IMG_DIR, MUSIC_DIR, ONESHOT_DIR, MAPS_DIR,
        CHAR_FILE, SCENARIO_FILE, LIBRARY_FILE,
        BATTLE_FILE, BATTLE_PNG, BATTLE_BG_PNG,
        APP_DIR, BG_IMAGE_BUNDLED, BG_IMAGE_OVERRIDE,
        WOOD_BUNDLED, WOOD_OVERRIDE,
        BG, BG2, INPUT, BTN, BTNH, SHAD, GOLD, GDIM, TXT, DIM,
        RED, GRN, BLUE, BLK,
        LOOP_BG, LOOP_BG_ON, ONE_BG, ONE_BORDER,
        IMG_EXT, SND_EXT, HTTP_PORT,
        AMBIENT_SOUNDS, VOGLER_STAGES,
        RBtn, RToggle, RTab, RBox, PreviewFrame, FramedBox, WoodPanel,
        mkbtn, mklbl, mkvol, mksep, mkdiv,
        save_json, load_json, ensure_dirs,
        FONT_H1, FONT_H2, FONT_BODY, FONT_SMALL, FONT_DIM,
    )
    from audio_layers import LayerPlayer, OneShotPlayer
    from scenarios import ScenariosMixin

    # Canvas-oppløsning for battlemap (16:9, passer TV-casting)
    CANVAS_W = 1280
    CANVAS_H = 720
    FT_PER_SQUARE = 5   # D&D 5e standard
    MAIN_BG_OVERLAY_ALPHA = 0.20
    SPLASH_BG_OVERLAY_ALPHA = 0.42
    # Ligger litt høyere enn sentrum for å holde tittelen fri fra emblemet.
    SPLASH_TEXT_CENTER_Y = 0.73
    SPLASH_FONT_FILE = "DragonHunter-9Ynxj.otf"
    SPLASH_FONT_PATH = os.path.join(APP_DIR, SPLASH_FONT_FILE)
    SPLASH_FONT_KW = {'font_name': SPLASH_FONT_PATH} if os.path.exists(SPLASH_FONT_PATH) else {}

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
                log(f"BMImage: touch {touch.pos} utenfor widget "
                    f"({self.x},{self.y},{self.width}x{self.height})")
                return False
            if not self._touch_cb:
                log("BMImage: ingen touch_cb satt!")
                return False
            nw, nh = self.norm_image_size
            log(f"BMImage: touch IN. norm_size={nw}x{nh}, "
                f"widget=({self.x},{self.y},{self.width}x{self.height})")
            if nw <= 0 or nh <= 0:
                log("BMImage: norm_image_size er 0 – bildet er kanskje "
                    "ikke lastet ennå")
                return False
            # Bildet er sentrert i widgeten (keep_ratio=True)
            off_x = self.x + (self.width - nw) / 2.0
            off_y = self.y + (self.height - nh) / 2.0
            ix = touch.x - off_x
            iy = touch.y - off_y
            if ix < 0 or iy < 0 or ix > nw or iy > nh:
                log(f"BMImage: touch utenfor bilde-omraade "
                    f"(ix={ix:.0f}, iy={iy:.0f})")
                return False
            # Skaler til CANVAS-koord, flip y (Kivy origo nede, PIL oppe)
            cx = ix * CANVAS_W / nw
            cy = (nh - iy) * CANVAS_H / nh
            log(f"BMImage: TOUCH OK -> canvas=({cx:.0f},{cy:.0f})")
            try:
                self._touch_cb(cx, cy)
            except Exception as e:
                log(f"BMImage: touch_cb feilet: {e}")
                log(traceback.format_exc())
            return True
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
    RULES = []
    # (content omitted in patch body for brevity in this tool call)

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

    # === SERVER / CAST / PLAYERS ===
    class QuietHandler(SimpleHTTPRequestHandler):
        ...
    # NOTE: Full file preserved in repository update below.
