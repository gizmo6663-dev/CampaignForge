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

    CANVAS_W = 1280
    CANVAS_H = 720
    FT_PER_SQUARE = 5
    MAIN_BG_OVERLAY_ALPHA = 0.20
    SPLASH_BG_OVERLAY_ALPHA = 0.42
    SPLASH_TEXT_CENTER_Y = 0.73
    SPLASH_FONT_FILE = "DragonHunter-9Ynxj.otf"
    SPLASH_FONT_PATH = os.path.join(APP_DIR, SPLASH_FONT_FILE)
    SPLASH_FONT_KW = {'font_name': SPLASH_FONT_PATH} if os.path.exists(SPLASH_FONT_PATH) else {}

    class _BMImage(Image):
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
            off_x = self.x + (self.width - nw) / 2.0
            off_y = self.y + (self.height - nh) / 2.0
            ix = touch.x - off_x
            iy = touch.y - off_y
            if ix < 0 or iy < 0 or ix > nw or iy > nh:
                return False
            cx = ix * CANVAS_W / nw
            cy = (nh - iy) * CANVAS_H / nh
            try:
                self._touch_cb(cx, cy)
            except Exception:
                log(traceback.format_exc())
            return True

    DND_ABILITIES = ['STR', 'DEX', 'CON', 'INT', 'WIS', 'CHA']
    DND_SKILLS = [('Acrobatics','DEX'),('Animal Handling','WIS'),('Arcana','INT'),('Athletics','STR'),('Deception','CHA'),('History','INT'),('Insight','WIS'),('Intimidation','CHA'),('Investigation','INT'),('Medicine','WIS'),('Nature','INT'),('Perception','WIS'),('Performance','CHA'),('Persuasion','CHA'),('Religion','INT'),('Sleight of Hand','DEX'),('Stealth','DEX'),('Survival','WIS')]

    def request_android_permissions():
        if platform != 'android': return
        try:
            from android.permissions import request_permissions, Permission
            request_permissions([Permission.READ_EXTERNAL_STORAGE, Permission.READ_MEDIA_IMAGES, Permission.READ_MEDIA_AUDIO, Permission.INTERNET, Permission.ACCESS_NETWORK_STATE, Permission.ACCESS_WIFI_STATE, Permission.CHANGE_WIFI_MULTICAST_STATE])
        except:
            pass

    class QuietHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            kwargs.pop('directory', None)
            super().__init__(*args, directory=BASE_DIR, **kwargs)
        def log_message(self, f, *a): pass
        def translate_path(self, path):
            clean = path.split('?', 1)[0].split('#', 1)[0].lstrip('/')
            for root in (DATA_DIR, BASE_DIR):
                cand = os.path.realpath(os.path.join(root, clean))
                real_root = os.path.realpath(root)
                if cand.startswith(real_root) and os.path.exists(cand):
                    return cand
            return os.path.join(BASE_DIR, clean)

    class MediaServer:
        def __init__(self): self._h = None
        def start(self):
            if self._h: return
            try:
                self._h = HTTPServer(('0.0.0.0', HTTP_PORT), QuietHandler)
                threading.Thread(target=self._h.serve_forever, daemon=True).start()
            except Exception as e:
                log(f"HTTP server start error: {e}")
        def stop(self):
            if self._h:
                self._h.shutdown(); self._h = None
        @staticmethod
        def ip():
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80)); r = s.getsockname()[0]; s.close(); return r
            except:
                return "127.0.0.1"
        def url(self, fp):
            real_fp = os.path.realpath(fp)
            for root in (DATA_DIR, BASE_DIR):
                real_root = os.path.realpath(root)
                if real_fp.startswith(real_root):
                    rel = os.path.relpath(real_fp, real_root)
                    if not rel.startswith('..'):
                        return f"http://{self.ip()}:{HTTP_PORT}/{rel.replace(os.sep, '/')}"
            return f"http://{self.ip()}:{HTTP_PORT}/{os.path.basename(fp)}"

    class CastMgr:
        def __init__(self): self.devices = {}; self.cc = None; self.mc = None; self._br = None
        def scan(self, cb=None):
            if not CAST_AVAILABLE: return
            self.devices = {}
            def _s():
                try:
                    ccs, br = pychromecast.get_chromecasts(); self._br = br
                except:
                    ccs = []
                for c in ccs: self.devices[c.cast_info.friendly_name] = c
                if cb: Clock.schedule_once(lambda dt: cb(list(self.devices.keys())), 0)
            threading.Thread(target=_s, daemon=True).start()
        def connect(self, name, cb=None):
            if name not in self.devices: return
            def _c():
                try:
                    c = self.devices[name]; c.wait(); self.cc = c; self.mc = c.media_controller; ok = True
                except:
                    ok = False
                if cb: Clock.schedule_once(lambda dt: cb(ok), 0)
            threading.Thread(target=_c, daemon=True).start()
        def cast_img(self, url, cb=None):
            if not self.mc: return
            def _c():
                try:
                    self.mc.play_media(url, 'image/jpeg'); self.mc.block_until_active(); ok = True
                except:
                    ok = False
                if cb: Clock.schedule_once(lambda dt: cb(ok), 0)
            threading.Thread(target=_c, daemon=True).start()
        def disconnect(self):
            try:
                if self._br: self._br.stop_discovery()
                if self.cc: self.cc.disconnect()
            except:
                pass
            self.cc = None; self.mc = None

    class APlayer:
        def __init__(self): self.mp = None; self.is_playing = False; self._v = 0.7
        def play(self, path):
            self.stop()
            try:
                self.mp = MediaPlayer(); self.mp.setDataSource(path); self.mp.setVolume(self._v, self._v); self.mp.prepare(); self.mp.start(); self.is_playing = True
            except:
                self.mp = None; self.is_playing = False
        def stop(self):
            if self.mp:
                try:
                    if self.mp.isPlaying(): self.mp.stop(); self.mp.release()
                except:
                    pass
                self.mp = None
            self.is_playing = False
        def pause(self):
            if self.mp and self.is_playing:
                try: self.mp.pause(); self.is_playing = False
                except: pass
        def resume(self):
            if self.mp and not self.is_playing:
                try: self.mp.start(); self.is_playing = True
                except: pass
        def vol(self, v):
            self._v = v
            if self.mp:
                try: self.mp.setVolume(v, v)
                except: pass

    class SPlayer:
        def __init__(self): self.mp = None; self.is_playing = False; self._v = 0.5
        def play_url(self, url):
            self.stop()
            if not USE_JNIUS: return False
            def _s():
                try:
                    self.mp = MediaPlayer(); self.mp.setDataSource(url); self.mp.setVolume(self._v, self._v); self.mp.prepare(); self.mp.start(); self.is_playing = True
                except Exception as e:
                    log(f"Stream err: {e}")
                    if self.mp:
                        try: self.mp.release()
                        except: pass
                        self.mp = None
                    self.is_playing = False
            threading.Thread(target=_s, daemon=True).start(); return True
        def stop(self):
            if self.mp:
                try:
                    if self.mp.isPlaying(): self.mp.stop(); self.mp.release()
                except:
                    pass
                self.mp = None
            self.is_playing = False
        def vol(self, v):
            self._v = v
            if self.mp:
                try: self.mp.setVolume(v, v)
                except: pass

    class FPlayer:
        def __init__(self):
            from kivy.core.audio import SoundLoader
            self.SL = SoundLoader; self.snd = None; self.is_playing = False; self._v = 0.7
        def play(self, path):
            self.stop(); self.snd = self.SL.load(path)
            if self.snd:
                self.snd.volume = self._v; self.snd.play(); self.is_playing = True
        def stop(self):
            if self.snd:
                try: self.snd.stop()
                except: pass
                self.snd = None
            self.is_playing = False
        def pause(self):
            if self.snd and self.is_playing:
                self.snd.stop(); self.is_playing = False
        def resume(self):
            if self.snd and not self.is_playing:
                self.snd.play(); self.is_playing = True
        def vol(self, v):
            self._v = v
            if self.snd: self.snd.volume = v

    class CampaignForgeApp(App, ScenariosMixin):
        _TAB_ORDER = ['img', 'lyd', 'tool', 'util']
        _TOOL_ORDER = ['chars', 'init']
        _UTIL_ORDER = ['map', 'rules', 'cast']

        def _resolve_theme_backgrounds(self):
            wood_path = WOOD_OVERRIDE if os.path.exists(WOOD_OVERRIDE) else WOOD_BUNDLED if os.path.exists(WOOD_BUNDLED) else None
            bg_path = BG_IMAGE_OVERRIDE if os.path.exists(BG_IMAGE_OVERRIDE) else BG_IMAGE_BUNDLED if os.path.exists(BG_IMAGE_BUNDLED) else None
            return wood_path, bg_path

        def _add_theme_background_layers(self, parent, wood_path=None, bg_path=None, overlay_alpha=0.35, base_color=None):
            if base_color:
                base = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
                with base.canvas:
                    from kivy.graphics import Color as _C, Rectangle as _R
                    _C(*base_color)
                    base_rect = _R(pos=base.pos, size=base.size)
                base.bind(pos=lambda w, v, r=base_rect: setattr(r, 'pos', w.pos), size=lambda w, v, r=base_rect: setattr(r, 'size', w.size))
                parent.add_widget(base)
            if wood_path:
                try:
                    wood_img = Image(source=wood_path, allow_stretch=True, keep_ratio=False, opacity=1.0, size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
                    parent.add_widget(wood_img)
                except Exception as e:
                    log(f"Tre-bakgrunn-feil: {e}")
            if bg_path:
                try:
                    bg_img = Image(source=bg_path, allow_stretch=True, keep_ratio=True, opacity=0.85, size_hint=(1, 0.63), pos_hint={'x': 0, 'y': 0})
                    parent.add_widget(bg_img)
                except Exception as e:
                    log(f"Emblem-feil: {e}")
            if overlay_alpha and (wood_path or bg_path):
                dim = Widget(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
                with dim.canvas:
                    from kivy.graphics import Color as _C, Rectangle as _R
                    _C(0, 0, 0, overlay_alpha)
                    dim_rect = _R(pos=dim.pos, size=dim.size)
                dim.bind(pos=lambda w, v, r=dim_rect: setattr(r, 'pos', w.pos), size=lambda w, v, r=dim_rect: setattr(r, 'size', w.size))
                parent.add_widget(dim)

        def build(self):
            log("=== BUILD (CampaignForge v0.1.0) ===")
            Window.clearcolor = BG
            self.title = "CampaignForge"
            self.tracks = []
            self.ct = -1
            self.sel_img = None
            self.preview_box = None
            self._gallery_open = False
            self.auto_cast = True
            self.cur_folder = IMG_DIR
            self.player = APlayer() if USE_JNIUS else FPlayer()
            self.streamer = SPlayer()
            self.oneshot = OneShotPlayer()
            self.cast = CastMgr()
            self.server = MediaServer()
            self.chars = load_json(CHAR_FILE, [])
            self.scenarios = load_json(SCENARIO_FILE, [])
            self.library = load_json(LIBRARY_FILE, [])
            self._enemies_data = {}
            try:
                enemies_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "enemies.json")
                if os.path.exists(enemies_path):
                    with open(enemies_path, 'r', encoding='utf-8') as f:
                        raw = json.load(f)
                    self._enemies_data = {k: v for k, v in raw.items() if not k.startswith('_')}
            except Exception as e:
                log(f"Failed to load enemies.json: {e}")
            self.edit_idx = None
            self._scn_view = 'list'
            self._scn_idx = None
            self._scn_scene_idx = None
            self._scn_layers = []
            self._scn_box_widgets = []
            self._scn_perf_mode = False

            wrapper = FloatLayout()
            wood_path, bg_path = self._resolve_theme_backgrounds()
            self._add_theme_background_layers(wrapper, wood_path, bg_path, overlay_alpha=MAIN_BG_OVERLAY_ALPHA)

            main = BoxLayout(orientation='vertical', spacing=0, size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            tabs = RBox(size_hint_y=None, height=dp(52), spacing=dp(4), padding=[dp(8), dp(4)], bg_color=BTN)
            self._tabs = {}
            left_tab_defs = [('img', 'Bilder'), ('lyd', 'Lyd')]
            right_tab_defs = [('tool', 'Karakter'), ('util', 'Verktøy')]
            for key, txt in left_tab_defs:
                active = key == 'img'
                b = RTab(text=txt, group='tabs', state='down' if active else 'normal', bg_color=BTNH if active else BTN, color=GOLD if active else DIM, font_size=sp(FONT_SMALL))
                b.bind(state=self._tab_color)
                b.bind(on_release=lambda x, k=key: self._tab(k))
                tabs.add_widget(b)
                self._tabs[key] = b
            tabs.add_widget(Widget(size_hint_x=None, width=dp(52)))
            for key, txt in right_tab_defs:
                b = RTab(text=txt, group='tabs', state='normal', bg_color=BTNH, color=DIM, font_size=sp(FONT_SMALL))
                b.bind(state=self._tab_color)
                b.bind(on_release=lambda x, k=key: self._tab(k))
                tabs.add_widget(b)
                self._tabs[key] = b
            main.add_widget(tabs)

            content_shell = RBox(bg_color=BG2)
            self.content = FloatLayout(size_hint=(1, 1))
            content_shell.add_widget(self.content)
            main.add_widget(content_shell)

            mp = RBox(size_hint_y=None, height=dp(48), spacing=dp(6), padding=[dp(10), dp(4)], bg_color=BTN)
            mp.add_widget(Widget(size_hint_x=None, width=dp(4)))
            self.mp_lbl = Label(text="Ingen musikk", font_size=sp(11), color=DIM, size_hint_x=0.45, halign='left')
            self.mp_lbl.bind(size=self.mp_lbl.setter('text_size'))
            mp.add_widget(self.mp_lbl)
            for t, cb in [("<<", self.prev_track), (">>", self.next_track)]:
                mp.add_widget(mkbtn(t, cb, small=True, size_hint_x=None, width=dp(44)))
            self.mp_btn = mkbtn("Play", self.toggle_play, accent=True, small=True, size_hint_x=None, width=dp(60))
            mp.add_widget(self.mp_btn)
            main.add_widget(mp)

            self.status = Label(text="", font_size=sp(10), color=DIM, size_hint_y=None, height=dp(20))
            main.add_widget(self.status)
            wrapper.add_widget(main)

            self.splash = FloatLayout(size_hint=(1, 1), pos_hint={'x': 0, 'y': 0})
            self._add_theme_background_layers(self.splash, wood_path, bg_path, overlay_alpha=SPLASH_BG_OVERLAY_ALPHA, base_color=BG)
            splash_text = BoxLayout(orientation='vertical', spacing=dp(4), size_hint=(1, None), height=dp(170), pos_hint={'center_x': 0.5, 'center_y': SPLASH_TEXT_CENTER_Y})
            t1 = Label(text="CAMPAIGN", font_size=sp(42), color=GOLD, bold=True, size_hint_y=None, height=dp(60), halign='center', **SPLASH_FONT_KW)
            t1.bind(size=t1.setter('text_size'))
            splash_text.add_widget(t1)
            t2 = Label(text="FORGE", font_size=sp(42), color=GDIM, bold=True, size_hint_y=None, height=dp(60), halign='center', **SPLASH_FONT_KW)
            t2.bind(size=t2.setter('text_size'))
            splash_text.add_widget(t2)
            sub = Label(text="Dungeon Master's Companion", font_size=sp(13), color=DIM, size_hint_y=None, height=dp(30), halign='center', **SPLASH_FONT_KW)
            sub.bind(size=sub.setter('text_size'))
            splash_text.add_widget(sub)
            self.splash.add_widget(splash_text)
            wrapper.add_widget(self.splash)

            self._cur_tab = 'img'
            self._tab('img')
            Clock.schedule_once(lambda dt: request_android_permissions(), 0.5)
            Clock.schedule_once(lambda dt: self._init(), 3)
            Clock.schedule_once(self._dismiss_splash, 3.5)
            return wrapper

        def _dismiss_splash(self, dt):
            if self.splash:
                anim = Animation(opacity=0, duration=1.3)
                def _remove(*a):
                    if self.splash.parent:
                        self.splash.parent.remove_widget(self.splash)
                    self.splash = None
                anim.bind(on_complete=_remove)
                anim.start(self.splash)

        def _tab_color(self, btn, state):
            if state == 'down':
                btn.bg_color = BTNH; btn.color = GOLD
            else:
                btn.bg_color = BTN; btn.color = DIM

        def _init(self):
            ensure_dirs(); self.server.start(); self._load_imgs(); self._load_tracks(); self.status.text = f"IP: {MediaServer.ip()}  |  Cast: {'Ja' if CAST_AVAILABLE else 'Nei'}"

        @staticmethod
        def _order_direction(old_key, new_key, order):
            if old_key is None or new_key is None or old_key == new_key: return 0
            try:
                old_i = order.index(old_key); new_i = order.index(new_key)
            except ValueError:
                return 1
            return 1 if new_i > old_i else -1

        def _slide_content(self, container, new_widget, direction):
            old_wrap = container.children[0] if container.children else None
            distance = container.width or Window.width or 1
            new_wrap = FloatLayout(size_hint=(1, 1), pos=(direction * distance, 0))
            new_widget.size_hint = (1, 1)
            new_widget.pos = (0, 0)
            new_wrap.add_widget(new_widget)
            container.add_widget(new_wrap)
            if old_wrap is None:
                new_wrap.x = 0
                return
            if direction not in (-1, 1):
                new_wrap.x = 0
                if old_wrap.parent is container:
                    container.remove_widget(old_wrap)
                return
            out_anim = Animation(x=-direction * distance, duration=0.20, t='out_quad')
            in_anim = Animation(x=0, duration=0.20, t='out_quad')
            def _remove_old(*_):
                if old_wrap.parent is container:
                    container.remove_widget(old_wrap)
            out_anim.bind(on_complete=_remove_old)
            out_anim.start(old_wrap)
            in_anim.start(new_wrap)

        def _build_tab_content(self, build_fn):
            """Build a tab page in isolation so we never reparent live widgets."""
            root = build_fn()
            if isinstance(root, Widget):
                return root
            return Widget(size_hint=(1, 1))

        def _tab(self, k):
            builders = {'img': self._mk_img, 'lyd': self._mk_lyd, 'tool': self._mk_tool, 'util': self._mk_util}
            if k in builders:
                if getattr(self, '_cur_tab', None) == k and self.content.children:
                    return
                direction = self._order_direction(getattr(self, '_cur_tab', k), k, self._TAB_ORDER)
                self._cur_tab = k
                new_widget = self._build_tab_content(builders[k])
                self._slide_content(self.content, new_widget, direction)

        def _gallery_collapsed_height(self): return dp(54)

        def _gallery_collapsed_content(self):
            body = BoxLayout(orientation='vertical', spacing=0)
            row = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6))
            prev_b = mkbtn("<", self._prev_img, small=True, size_hint_x=None); prev_b.width = dp(46)
            row.add_widget(prev_b)
            row.add_widget(mkbtn("Galleri", self._toggle_gallery, accent=True, small=True))
            next_b = mkbtn(">", self._next_img, small=True, size_hint_x=None); next_b.width = dp(46)
            row.add_widget(next_b)
            body.add_widget(row)
            body.add_widget(Widget(size_hint_y=1.0))
            return body

        def _apply_gallery_collapsed_shell(self, gallery_wrap):
            gallery_wrap.clear_widgets(); gallery_wrap.orientation = 'vertical'; gallery_wrap.spacing = 0; gallery_wrap.padding = [dp(8), dp(6), dp(8), dp(6)]; gallery_wrap.tex_offset_x = 0.0; gallery_wrap.tint_color = [1.0, 0.78, 0.45, 0.14]; gallery_wrap.add_widget(self._gallery_collapsed_content())

        def _apply_gallery_open_shell(self, gallery_wrap):
            gallery_wrap.clear_widgets(); gallery_wrap.orientation = 'vertical'; gallery_wrap.spacing = dp(4); gallery_wrap.padding = [dp(6), dp(6), dp(6), dp(6)]; gallery_wrap.tex_offset_x = 0.0; gallery_wrap.tint_color = [1.0, 0.78, 0.45, 0.14]
            gh = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(4))
            gh.add_widget(mkbtn("Opp", self.folder_up, small=True, size_hint_x=None, width=dp(54)))
            gh.add_widget(self.path_lbl)
            gh.add_widget(self.ac_btn)
            gh.add_widget(mkbtn("Oppdater", self._load_imgs, small=True, size_hint_x=None, width=dp(80)))
            gh.add_widget(mkbtn("x", self._toggle_gallery, danger=True, small=True, size_hint_x=None, width=dp(40)))
            gallery_wrap.add_widget(gh)
            if self._gallery_scroll is None:
                self._gallery_scroll = ScrollView()
            if self.img_grid.parent:
                self.img_grid.parent.remove_widget(self.img_grid)
            if self._gallery_scroll.parent:
                self._gallery_scroll.parent.remove_widget(self._gallery_scroll)
            self._gallery_scroll.clear_widgets()
            self._gallery_scroll.add_widget(self.img_grid)
            gallery_wrap.add_widget(self._gallery_scroll)

        def _gallery_open_target_height(self):
            fa = getattr(self, '_float_area', None)
            if fa and fa.height > dp(100): return max(fa.height - dp(4), dp(80))
            _preview_h = dp(240); _spacing = dp(6) * 2
            return max(self.content.height - _preview_h - _spacing - dp(4), dp(80))

        def _mk_img(self):
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            preview_box = PreviewFrame(size_hint_y=None, height=dp(240), padding=dp(10), has_content=bool(self.sel_img))
            self.preview = Image(allow_stretch=True, keep_ratio=True, color=[1, 1, 1, 0] if not self.sel_img else [1, 1, 1, 1])
            self.preview_box = preview_box
            if self.sel_img: self.preview.source = self.sel_img
            preview_box.add_widget(self.preview)
            p.add_widget(preview_box)
            self._img_root = p
            self.path_lbl = Label(text="", font_size=sp(10), color=DIM, size_hint_x=0.30, halign='left', valign='middle')
            self.path_lbl.bind(size=lambda w, v: setattr(w, 'text_size', v))
            self.ac_btn = mkbtn("AC:PA" if self.auto_cast else "AC:AV", self._toggle_ac, accent=True, small=True, size_hint_x=None)
            self.ac_btn.width = dp(72)
            float_area = FloatLayout(size_hint=(1, 1))
            self._float_area = float_area
            title_lbl = Label(text="CAMPAIGN FORGE", font_size=sp(18), color=GDIM, bold=True, size_hint=(1, None), height=dp(28), halign='center', **SPLASH_FONT_KW)
            title_lbl.bind(size=title_lbl.setter('text_size'))
            self.img_lbl = Label(text="", font_size=sp(12), color=DIM, size_hint=(1, None), height=dp(20), halign='center')
            self.img_lbl.bind(size=self.img_lbl.setter('text_size'))
            text_box = BoxLayout(orientation='vertical', spacing=dp(4), size_hint=(1, None), height=dp(52), pos_hint={'x': 0, 'y': 0})
            text_box.add_widget(title_lbl); text_box.add_widget(self.img_lbl); float_area.add_widget(text_box)
            self.img_grid = GridLayout(cols=3, spacing=dp(6), padding=dp(6), size_hint_y=None)
            self.img_grid.bind(minimum_height=self.img_grid.setter('height'))
            wood_src = WOOD_OVERRIDE if os.path.exists(WOOD_OVERRIDE) else WOOD_BUNDLED if os.path.exists(WOOD_BUNDLED) else ""
            self._gallery_scroll = ScrollView()
            if self._gallery_open:
                gallery_wrap = WoodPanel(orientation='vertical', spacing=dp(4), size_hint=(1, None), pos_hint={'x': 0, 'top': 1}, height=self._gallery_open_target_height(), padding=[dp(6), dp(6), dp(6), dp(6)], wood_source=wood_src, tex_offset_x=0.0, tint_color=[1.0, 0.78, 0.45, 0.14])
                self._apply_gallery_open_shell(gallery_wrap)
            else:
                gallery_wrap = WoodPanel(orientation='vertical', spacing=0, size_hint=(1, None), pos_hint={'x': 0, 'top': 1}, height=self._gallery_collapsed_height(), padding=[dp(8), dp(6), dp(8), dp(6)], wood_source=wood_src, tex_offset_x=0.0, tint_color=[1.0, 0.78, 0.45, 0.14])
                self._apply_gallery_collapsed_shell(gallery_wrap)
            float_area.add_widget(gallery_wrap)
            self._gallery_wrap = gallery_wrap
            p.add_widget(float_area)
            self._load_imgs(); return p

        def _toggle_gallery(self, *a):
            if getattr(self, '_gallery_animating', False): return
            self._gallery_animating = True
            gw = getattr(self, '_gallery_wrap', None)
            fa = getattr(self, '_float_area', None)
            if not gw or not fa:
                self._gallery_open = not self._gallery_open; self._cur_tab = 'img'; self._tab('img'); self._gallery_animating = False; return
            Animation.cancel_all(gw, 'height')
            if self._gallery_open:
                def _close_done(*_):
                    self._gallery_open = False
                    self._cur_tab = 'img'
                    self._tab('img')
                    self._gallery_animating = False
                _close_anim = Animation(height=self._gallery_collapsed_height(), duration=0.22, transition='out_quad')
                _close_anim.bind(on_complete=_close_done); _close_anim.start(gw)
            else:
                self._apply_gallery_open_shell(gw); self._load_imgs(); target_h = self._gallery_open_target_height()
                def _open_done(*_):
                    self._gallery_open = True
                    self._cur_tab = 'img'
                    self._tab('img')
                    self._gallery_animating = False
                _open_anim = Animation(height=target_h, duration=0.22, transition='out_quad')
                _open_anim.bind(on_complete=_open_done); _open_anim.start(gw)

        def _gallery_image_paths(self):
            f = self.cur_folder
            try:
                if not os.path.exists(f): return []
                items = sorted(os.listdir(f))
                return [os.path.join(f, x) for x in items if x.lower().endswith(IMG_EXT)]
            except Exception:
                return []

        def _prev_img(self, *a):
            paths = self._gallery_image_paths()
            if not paths: return
            idx = paths.index(self.sel_img) - 1 if self.sel_img in paths else len(paths) - 1
            self._sel_img(paths[idx % len(paths)])

        def _next_img(self, *a):
            paths = self._gallery_image_paths()
            if not paths: return
            idx = paths.index(self.sel_img) + 1 if self.sel_img in paths else 0
            self._sel_img(paths[idx % len(paths)])

        def _load_imgs(self):
            if not hasattr(self, 'img_grid'): return
            self.img_grid.clear_widgets(); f = self.cur_folder
            rel = os.path.relpath(f, IMG_DIR) if f != IMG_DIR else ""
            self.path_lbl.text = f"/{rel}" if rel else "/"
            try:
                if not os.path.exists(f):
                    self.img_lbl.text = "Mappe ikke funnet"
                    self.img_grid.add_widget(mklbl("Mappen finnes ikke ennå.\nStart appen på nytt etter å ha\ngodtatt tillatelser.", color=DIM, size=11, wrap=True))
                    return
                items = sorted(os.listdir(f))
                dirs = [d for d in items if os.path.isdir(os.path.join(f, d)) and not d.startswith('.')]
                imgs = [x for x in items if x.lower().endswith(IMG_EXT)]
                self.img_lbl.text = f"{len(dirs)} mapper, {len(imgs)} bilder"
                if not dirs and not imgs:
                    self.img_grid.add_widget(mklbl("Ingen bilder funnet.\n\nLegg bilder i:\nDokumenter/CampaignForge/images/\n\nTips: lag undermapper for\nå organisere etter scenario,\nf.eks. images/Slow Boat/\n\nStøttede formater:\n.png  .jpg  .jpeg  .webp", color=DIM, size=11, wrap=True)); return
                for d in dirs:
                    self.img_grid.add_widget(mkbtn(f"[{d}]", lambda dn=d: self._enter(dn), accent=True, small=True, size_hint_y=None, height=dp(70)))
                for fn in imgs:
                    path = os.path.join(f, fn)
                    img = Image(source=path, allow_stretch=True, keep_ratio=True, size_hint_y=None, height=dp(100), mipmap=True)
                    img._path = path; img.bind(on_touch_down=self._img_touch); self.img_grid.add_widget(img)
            except Exception as e:
                log(f"load_imgs: {e}")

        def _img_touch(self, w, touch):
            if w.collide_point(*touch.pos):
                self._sel_img(w._path); return True
            return False

        def _enter(self, name):
            self.cur_folder = os.path.join(self.cur_folder, name); self._load_imgs()

        def folder_up(self):
            if self.cur_folder != IMG_DIR:
                self.cur_folder = os.path.dirname(self.cur_folder); self._load_imgs()

        def _sel_img(self, path):
            self.sel_img = path
            if self.preview_box: self.preview_box.has_content = True
            self.img_lbl.text = os.path.basename(path); self.img_lbl.color = GOLD
            Animation.cancel_all(self.preview, 'opacity')
            fade_out = Animation(opacity=0, duration=0.3)
            def _swap(*a):
                self.preview.source = path; Animation(opacity=1, duration=0.4).start(self.preview)
                if self.auto_cast and self.cast.mc:
                    if hasattr(self, '_bm_cast_live'): self._bm_cast_live = False
                    self.img_lbl.text = "Caster..."
                    self.cast.cast_img(self.server.url(path), cb=lambda ok: setattr(self.img_lbl, 'text', "Castet!" if ok else "Feilet"))
            fade_out.bind(on_complete=_swap)
            self.preview.color = [1, 1, 1, 1]
            fade_out.start(self.preview)

        def _toggle_ac(self):
            self.auto_cast = not self.auto_cast
            self.ac_btn.text = f"AC:{'PA' if self.auto_cast else 'AV'}"

        def _mk_mus(self):
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            self.trk_lbl = Label(text="Velg et spor", font_size=sp(14), color=DIM, size_hint_y=None, height=dp(34), bold=True)
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
            self._load_tracks(); return p

        def _load_tracks(self):
            if not hasattr(self, 'trk_grid'): return
            self.trk_grid.clear_widgets(); self.tracks = []
            try:
                if not os.path.exists(MUSIC_DIR):
                    self.trk_lbl.text = "Mappe ikke funnet"
                    self.trk_grid.add_widget(mklbl("Musikkmappen finnes ikke ennå.\nStart appen på nytt etter å ha\ngodtatt tillatelser.", color=DIM, size=11, wrap=True)); return
                fl = sorted([f for f in os.listdir(MUSIC_DIR) if f.lower().endswith(('.mp3','.ogg','.wav','.flac'))])
                self.trk_lbl.text = f"{len(fl)} spor"
                if not fl:
                    self.trk_grid.add_widget(mklbl("Ingen musikkfiler funnet.\n\nLegg lydfiler i:\nDokumenter/CampaignForge/music/\n\nStøttede formater:\n.mp3  .ogg  .wav  .flac", color=DIM, size=11, wrap=True)); return
                for i, fn in enumerate(fl):
                    self.tracks.append(os.path.join(MUSIC_DIR, fn))
                    self.trk_grid.add_widget(mkbtn(fn, lambda idx=i: self.play_track(idx), small=True, size_hint_y=None, height=dp(42)))
            except Exception as e:
                log(f"load_tracks: {e}")

        def play_track(self, idx):
            if idx < 0 or idx >= len(self.tracks): return
            self.ct = idx; self.player.play(self.tracks[idx]); n = os.path.basename(self.tracks[idx]); self.trk_lbl.text = f"Spiller: {n}"; self.trk_lbl.color = GOLD; self.mp_lbl.text = n; self.mp_btn.text = "Pause"
        def toggle_play(self):
            if not self.player.is_playing and self.ct < 0:
                if self.tracks: self.play_track(0); return
            if self.player.is_playing: self.player.pause(); self.mp_btn.text = "Play"
            else: self.player.resume(); self.mp_btn.text = "Pause"
        def stop_music(self): self.player.stop(); self.mp_btn.text = "Play"; self.mp_lbl.text = "Stoppet"; self.trk_lbl.text = "Stoppet"
        def next_track(self):
            if self.tracks: self.play_track((self.ct + 1) % len(self.tracks))
        def prev_track(self):
            if self.tracks: self.play_track((self.ct - 1) % len(self.tracks))

        def _mk_amb(self):
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            scroll = ScrollView()
            g = GridLayout(cols=1, spacing=dp(4), padding=dp(6), size_hint_y=None)
            g.bind(minimum_height=g.setter('height'))
            for snd in AMBIENT_SOUNDS:
                if 'url' not in snd:
                    g.add_widget(mklbl(snd['name'], color=GDIM, size=11, bold=True, h=24))
                else:
                    g.add_widget(mkbtn(snd['name'], lambda u=snd['url'], n=snd['name']: self._pa(u, n), small=True, size_hint_y=None, height=dp(40)))
            scroll.add_widget(g)
            p.add_widget(scroll)
            p.add_widget(mkbtn("Stopp ambient", self._sa, danger=True, size_hint_y=None, height=dp(44)))
            p.add_widget(mkvol(self.streamer.vol, 0.5))
            self.amb_lbl = mklbl("", color=DIM, size=11, h=20)
            p.add_widget(self.amb_lbl)
            p.add_widget(Widget(size_hint_y=1))
            return p

        def _pa(self, url, name): self._an = name; self._ac = 0; self.amb_lbl.text = f"Laster: {name}..."; 
        def _poll(self, dt): return False
        def _sa(self): self.streamer.stop(); self.amb_lbl.text = "Stoppet"; self.amb_lbl.color = DIM

        def _mk_rules(self):
            p = BoxLayout(orientation='vertical', spacing=dp(4), padding=dp(4)); self._rules_expanded = set(); self._rules_overlay = None
            hdr = BoxLayout(size_hint_y=None, height=dp(34)); hdr.add_widget(mklbl("REGLER & REFERANSE", color=GOLD, size=15, bold=True)); p.add_widget(hdr); p.add_widget(mksep(2))
            scroll = ScrollView(); self._rules_tree = GridLayout(cols=1, spacing=dp(2), padding=dp(4), size_hint_y=None); self._rules_tree.bind(minimum_height=self._rules_tree.setter('height')); scroll.add_widget(self._rules_tree); p.add_widget(scroll); self._rules_main = p; self._rules_build_tree(); return p
        def _rules_build_tree(self): self._rules_tree.clear_widgets()
        def _rules_toggle(self, cat_idx): pass
        def _rules_open(self, cat_idx, sub_idx): pass
        def _rules_close_overlay(self): self._rules_overlay = None; self._rules_dim = None

        def _mk_cast(self):
            p = BoxLayout(orientation='vertical', spacing=dp(10), padding=dp(10))
            if not CAST_AVAILABLE:
                p.add_widget(mklbl("Casting utilgjengelig\npychromecast mangler", color=DIM, size=13)); return p
            self.cast_lbl = mklbl("Ikke tilkoblet", color=DIM, size=13, h=30)
            p.add_widget(self.cast_lbl)
            p.add_widget(mkbtn("Sok etter enheter", self._scan, accent=True, size_hint_y=None, height=dp(46)))
            self.cast_sp = Spinner(text="Velg enhet...", values=[], size_hint_y=None, height=dp(46), background_color=BTN, color=TXT)
            p.add_widget(self.cast_sp)
            r = BoxLayout(size_hint_y=None, height=dp(46), spacing=dp(10))
            r.add_widget(mkbtn("Koble til", self._cn, accent=True)); r.add_widget(mkbtn("Koble fra", self._dc, danger=True)); p.add_widget(r)
            p.add_widget(Widget(size_hint_y=1)); return p
        def _scan(self): self.cast_lbl.text = "Soker..."; self.cast.scan(cb=self._od)
        def _od(self, n):
            if n: self.cast_sp.values = n; self.cast_sp.text = n[0]
            self.cast_lbl.text = f"Fant {len(n)}" if n else "Ingen"
        def _cn(self):
            n = self.cast_sp.text
            if not n or n == "Velg enhet...": return
            self.cast.connect(n, cb=lambda ok: setattr(self.cast_lbl, 'text', "Tilkoblet!" if ok else "Feilet"))
        def _dc(self): self.cast.disconnect(); self.cast_lbl.text = "Frakoblet"

        def _mk_tool(self):
            self._init_tracker_init()
            if not hasattr(self, '_tool_sub'): self._tool_sub = 'chars'
            elif self._tool_sub not in ('chars', 'init'): self._tool_sub = 'chars'
            p = BoxLayout(orientation='vertical', spacing=dp(6))
            sub_bar = RBox(size_hint_y=None, height=dp(42), spacing=dp(4), padding=[dp(6), dp(4)], bg_color=BTN, radius=dp(10))
            def _mk_tool_sub(key, label):
                act = self._tool_sub == key
                b = RTab(text=label, group='tool_sub', state='down' if act else 'normal', bg_color=BTNH if act else BTN, color=GOLD if act else DIM, font_size=sp(11), bold=True)
                def _on_state(btn, st):
                    if st == 'down': btn.bg_color = BTNH; btn.color = GOLD
                    else: btn.bg_color = BTN; btn.color = DIM
                b.bind(state=_on_state); b.bind(on_release=lambda btn, k=key: self._tool_switch(k)); return b
            sub_bar.add_widget(_mk_tool_sub('chars', 'Karakterer')); sub_bar.add_widget(_mk_tool_sub('init', 'Initiativ')); p.add_widget(sub_bar)
            self._tool_action_bar = BoxLayout(size_hint_y=None, height=dp(42), spacing=dp(6), padding=[dp(6), 0]); p.add_widget(self._tool_action_bar)
            self.tool_area = FloatLayout(); p.add_widget(self.tool_area)
            self._tool_render_sub(); return p

        def _tool_switch(self, which):
            if getattr(self, '_tool_sub', None) == which: return
            prev = getattr(self, '_tool_sub', which); self._tool_slide_dir = self._order_direction(prev, which, self._TOOL_ORDER); self._tool_sub = which; self._tool_render_sub()
        def _tool_render_sub(self): pass
        def _util_render_sub(self): pass

        def _show_list(self):
            self.tool_area.clear_widgets(); scroll = ScrollView(); g = GridLayout(cols=1, spacing=dp(6), padding=dp(6), size_hint_y=None); g.bind(minimum_height=g.setter('height'))
            if not self.chars: g.add_widget(mklbl("Ingen karakterer ennå.\nTrykk '+ Ny' for å lage en.", color=DIM, size=12, h=50))
            scroll.add_widget(g); self.tool_area.add_widget(scroll)

        def _mk_init_tracker(self):
            self.tool_area.clear_widgets(); self.tool_area.add_widget(BoxLayout())
        def _battle_state_init(self): pass
        def _mk_battle_map(self): pass
        def _battle_render(self): pass
        def _battle_build_stat_panel(self): pass
        def _battle_refresh_img(self): pass
        def _battle_sync_cast_if_live(self): pass
        def _battle_cast_current(self, success_msg=None, error_msg=None): pass
        def _battle_mode_switch(self, mode): pass
        def _battle_on_map_touch(self, cx, cy): pass
        def _battle_handle_move_tap(self, col, row): pass
        def _battle_toggle_fog(self, col, row): pass
        def _battle_handle_measure_tap(self, col, row): pass
        def _battle_next_turn(self): pass
        def _battle_color_for_type(self, tp): pass
        def _battle_show_menu(self): pass
        def _battle_toggle_grid(self): pass
        def _battle_set_cols(self, n): pass
        def _battle_fill_fog(self): pass
        def _battle_clear_fog(self): pass
        def _battle_set_pc_vis(self, radius): pass
        def _battle_clear_tokens(self): pass
        def _battle_clear_bg(self): pass
        def _battle_sync_from_init(self): pass
        def _battle_cast(self): pass
        def _battle_pick_bg(self): pass
        def _battle_set_bg(self, path): pass

        def on_stop(self):
            self.player.stop(); self.streamer.stop();
            for lp in getattr(self, '_scn_layers', []):
                if lp:
                    try: lp.stop()
                    except: pass
            try: self.oneshot.stop_all()
            except: pass
            self.server.stop(); self.cast.disconnect(); save_json(CHAR_FILE, self.chars); save_json(SCENARIO_FILE, self.scenarios); save_json(LIBRARY_FILE, self.library)
            if hasattr(self, '_bm_init_done'): self._battle_save()

    log("Starting app...")
    CampaignForgeApp().run()

except Exception as e:
    log(f"CRASH: {e}")
    log(traceback.format_exc())
