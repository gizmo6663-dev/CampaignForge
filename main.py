import os, sys, traceback, socket, threading, json, random
from http.server import HTTPServer, SimpleHTTPRequestHandler
from functools import partial
from kivy.clock import Clock

LOG = "/sdcard/Documents/CampaignForge/crash.log"
os.makedirs(os.path.dirname(LOG), exist_ok=True)
def log(msg):
    with open(LOG, "a") as f:
        f.write(msg + "\n")
log("=== APP START (Campaign Forge v0.1.2 – Golden Realm) ===")

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
    TRACKER_FILE = os.path.join(BASE_DIR, "trackers.json")
    NPC_FILE = os.path.join(BASE_DIR, "npcs.json")

    def ensure_dirs():
        for d in [IMG_DIR, MUSIC_DIR]:
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                log(f"makedirs {d}: {e}")
        log(f"Dirs OK: {os.path.exists(IMG_DIR)}, {os.path.exists(MUSIC_DIR)}")

    # === FARGER – GOLDEN REALM ===
    BG   = [0.08, 0.10, 0.14, 1]
    BG2  = [0.12, 0.15, 0.20, 1]
    BTN  = [0.15, 0.18, 0.24, 1]
    BTNH = [0.25, 0.32, 0.44, 1]
    SHAD = [0.02, 0.02, 0.04, 0.6]
    GOLD = [0.95, 0.78, 0.22, 1]
    GDIM = [0.58, 0.45, 0.20, 1]
    SMRG = [0.20, 0.50, 0.30, 1]
    SMRG_DIM = [0.12, 0.30, 0.18, 1]
    TXT  = [0.90, 0.92, 0.95, 1]
    DIM  = [0.52, 0.58, 0.68, 1]
    RED  = [0.80, 0.25, 0.25, 1]
    GRN  = [0.30, 0.65, 0.35, 1]
    BLUE = [0.35, 0.55, 0.80, 1]
    BLK  = [0.0, 0.0, 0.0, 1]
    IMG_EXT   = ('.png','.jpg','.jpeg','.webp')
    HTTP_PORT = 8089

    class RBtn(Button):
        bg_color = ListProperty(BTN)
        hover_color = ListProperty(BTNH)
        shadow_color = ListProperty(SHAD)
        radius = NumericProperty(dp(8))

    # ============================================================
    # KV REGLER – FIXED: alt i canvas.before
    # ============================================================
    Builder.load_string('''
#:kivy 2.0

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
            rgba: self.bg_color if self.state == 'normal' else self.hover_color
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [self.radius]

<RLabel@Label>:
    text_size: self.width, None
    markup: True
    halign: 'left'
    valign: 'top'
''')

    # ============================================================
    # CHARACTER SYSTEM – D&D 5e
    # ============================================================
    class D20Character:
        def __init__(self, name="Ukjent", data=None):
            if data:
                self.__dict__.update(data)
            else:
                self.name = name
                self.class_name = "Fighter"
                self.race = "Human"
                self.level = 1
                self.xp = 0
                self.alignment = "Neutral"
                self.background = "Soldier"
                self.str = 10
                self.dex = 10
                self.con = 10
                self.int = 10
                self.wis = 10
                self.cha = 10
                self.hp_max = 8
                self.hp_current = 8
                self.ac = 10
                self.speed = 30
                self.initiative_bonus = 0
                self.proficiency_bonus = 2
                self.saving_throws = {t: False for t in ['str','dex','con','int','wis','cha']}
                self.skill_proficiencies = {s: False for s in [
                    'acrobatics','animal_handling','arcana','athletics','deception',
                    'history','insight','intimidation','investigation','medicine',
                    'nature','perception','performance','persuasion','religion',
                    'sleight_of_hand','stealth','survival'
                ]}
                self.conditions = []
                self.hit_dice = "d8"
                self.inspiration = False
                self.spell_slots = {}
                self.spells_known = []

        def get_modifier(self, ability):
            score = getattr(self, ability, 10)
            return (score - 10) // 2

        def to_dict(self):
            return self.__dict__

    def load_characters():
        try:
            if os.path.exists(CHAR_FILE):
                with open(CHAR_FILE, 'r') as f:
                    data = json.load(f)
                    return {name: D20Character(name, char_data) for name, char_data in data.items()}
        except Exception as e:
            log(f"load_characters error: {e}")
        return {}

    def save_characters(characters):
        try:
            data = {name: char.to_dict() for name, char in characters.items()}
            os.makedirs(os.path.dirname(CHAR_FILE), exist_ok=True)
            with open(CHAR_FILE, 'w') as f:
                json.dump(data, f, indent=2)
            log(f"Characters saved: {list(data.keys())}")
        except Exception as e:
            log(f"save_characters error: {e}")

    # ============================================================
    # VERKTØY
    # ============================================================
    class D20Roller:
        @staticmethod
        def roll_d20(bonus=0):
            return random.randint(1, 20) + bonus

        @staticmethod
        def roll_dice(dice_str):
            try:
                parts = dice_str.replace(' ', '').split('+')
                dice_part = parts[0]
                bonus = int(parts[1]) if len(parts) > 1 else 0
                num, sides = map(int, dice_part.split('d'))
                rolls = [random.randint(1, sides) for _ in range(num)]
                total = sum(rolls) + bonus
                return {'rolls': rolls, 'bonus': bonus, 'total': total}
            except Exception as e:
                log(f"roll_dice error: {e}")
                return None

    # ============================================================
    # IMAGE GALLERY
    # ============================================================
    class ImageGallery(ScrollView):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.current_folder = IMG_DIR
            self.folder_stack = [IMG_DIR]

            self.main_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None)
            self.main_layout.bind(minimum_height=self.main_layout.setter('height'))
            self.add_widget(self.main_layout)
            self.refresh_gallery()

        def refresh_gallery(self):
            self.main_layout.clear_widgets()

            if len(self.folder_stack) > 1:
                btn_back = RBtn(
                    text='← Tilbake',
                    size_hint_y=None,
                    height=dp(50),
                    bg_color=BTN,
                    hover_color=SMRG_DIM,
                    shadow_color=SHAD,
                    radius=dp(8)
                )
                btn_back.bind(on_press=self.go_back)
                self.main_layout.add_widget(btn_back)

            try:
                items = sorted(os.listdir(self.current_folder))
                for item in items:
                    path = os.path.join(self.current_folder, item)
                    if os.path.isdir(path):
                        btn = RBtn(
                            text=f'📁 {item}',
                            size_hint_y=None,
                            height=dp(50),
                            bg_color=BTN,
                            hover_color=SMRG,
                            shadow_color=SHAD,
                            radius=dp(8)
                        )
                        btn.bind(on_press=partial(self.open_folder, path))
                        self.main_layout.add_widget(btn)
                    elif any(item.lower().endswith(ext) for ext in IMG_EXT):
                        img_layout = BoxLayout(size_hint_y=None, height=dp(250))
                        img = Image(source=path)
                        img_layout.add_widget(img)
                        self.main_layout.add_widget(img_layout)
            except Exception as e:
                log(f"Gallery error: {e}")

        def open_folder(self, path, *args):
            self.folder_stack.append(path)
            self.current_folder = path
            self.refresh_gallery()

        def go_back(self, *args):
            if len(self.folder_stack) > 1:
                self.folder_stack.pop()
                self.current_folder = self.folder_stack[-1]
                self.refresh_gallery()

    # ============================================================
    # MUSIC PLAYER
    # ============================================================
    class MusicPlayer(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.spacing = dp(10)
            self.padding = dp(10)
            self.current_track = None
            self.mp = None

            header = Label(
                text='🎵 Musikk',
                size_hint_y=None,
                height=dp(40),
                color=GOLD,
                font_size=sp(18),
                bold=True
            )
            self.add_widget(header)

            track_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            self.track_spinner = Spinner(
                text='Velg musikk...',
                values=self.get_music_files(),
                size_hint_x=0.7
            )
            self.track_spinner.bind(text=self.on_track_selected)
            track_layout.add_widget(self.track_spinner)

            play_btn = RBtn(
                text='▶',
                size_hint_x=0.15,
                bg_color=SMRG,
                hover_color=SMRG_DIM,
                shadow_color=SHAD,
                radius=dp(8)
            )
            play_btn.bind(on_press=self.play_track)
            track_layout.add_widget(play_btn)

            stop_btn = RBtn(
                text='⏹',
                size_hint_x=0.15,
                bg_color=RED,
                hover_color=[1, 0.4, 0.4, 1],
                shadow_color=SHAD,
                radius=dp(8)
            )
            stop_btn.bind(on_press=self.stop_track)
            track_layout.add_widget(stop_btn)

            self.add_widget(track_layout)

            self.info_label = Label(
                text='Ingen musikk spiller',
                size_hint_y=None,
                height=dp(30),
                color=DIM,
                font_size=sp(12)
            )
            self.add_widget(self.info_label)

        def get_music_files(self):
            try:
                files = [f for f in os.listdir(MUSIC_DIR) if f.endswith(('.mp3', '.wav', '.ogg'))]
                return files if files else ['Ingen musikk']
            except Exception as e:
                log(f"get_music_files error: {e}")
                return ['Ingen musikk']

        def on_track_selected(self, spinner, text):
            if text != 'Ingen musikk':
                self.current_track = os.path.join(MUSIC_DIR, text)
            else:
                self.current_track = None

        def play_track(self, *args):
            if self.current_track and USE_JNIUS:
                try:
                    if self.mp:
                        self.mp.stop()
                    self.mp = MediaPlayer()
                    self.mp.setDataSource(self.current_track)
                    self.mp.prepare()
                    self.mp.start()
                    self.info_label.text = f'▶ {os.path.basename(self.current_track)}'
                except Exception as e:
                    log(f"Playback error: {e}")
                    self.info_label.text = 'Feil ved avspilling'
            elif not self.current_track:
                self.info_label.text = 'Velg musikk først'

        def stop_track(self, *args):
            if self.mp:
                try:
                    self.mp.stop()
                    self.mp.release()
                    self.mp = None
                    self.info_label.text = 'Stoppet'
                except Exception as e:
                    log(f"stop_track error: {e}")

    # ============================================================
    # AMBIENT SOUNDS
    # ============================================================
    class AmbientSounds(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.spacing = dp(10)
            self.padding = dp(10)
            self.mp = None

            header = Label(
                text='🌫️ Ambient',
                size_hint_y=None,
                height=dp(40),
                color=GOLD,
                font_size=sp(18),
                bold=True
            )
            self.add_widget(header)

            ambients = [
                ('Tavern', 'https://archive.org/download/ambience-tavern/tavern-loop.mp3'),
                ('Forest', 'https://archive.org/download/ambience-forest/forest-loop.mp3'),
                ('Castle', 'https://archive.org/download/ambience-castle/castle-loop.mp3'),
                ('Battle', 'https://archive.org/download/ambience-battle/battle-loop.mp3'),
            ]

            for name, url in ambients:
                btn = RBtn(
                    text=name,
                    size_hint_y=None,
                    height=dp(50),
                    bg_color=SMRG_DIM,
                    hover_color=SMRG,
                    shadow_color=SHAD,
                    radius=dp(8)
                )
                btn.bind(on_press=partial(self.play_ambient, url, name))
                self.add_widget(btn)

            stop_btn = RBtn(
                text='⏹ Stopp',
                size_hint_y=None,
                height=dp(50),
                bg_color=RED,
                hover_color=[1, 0.4, 0.4, 1],
                shadow_color=SHAD,
                radius=dp(8)
            )
            stop_btn.bind(on_press=self.stop_ambient)
            self.add_widget(stop_btn)

            self.info_label = Label(
                text='',
                size_hint_y=None,
                height=dp(30),
                color=DIM,
                font_size=sp(12)
            )
            self.add_widget(self.info_label)

        def play_ambient(self, url, name, *args):
            if USE_JNIUS:
                try:
                    if self.mp:
                        self.mp.stop()
                        self.mp.release()
                    self.mp = MediaPlayer()
                    self.mp.setDataSource(url)
                    self.mp.setLooping(True)
                    self.mp.prepareAsync()
                    self.mp.setOnPreparedListener(
                        _PreparedListener(self.mp)
                    )
                    self.info_label.text = f'Laster {name}...'
                except Exception as e:
                    log(f"Ambient error: {e}")
                    self.info_label.text = 'Feil ved avspilling'
            else:
                self.info_label.text = 'Ambient ikke tilgjengelig'

        def stop_ambient(self, *args):
            if self.mp:
                try:
                    self.mp.stop()
                    self.mp.release()
                    self.mp = None
                    self.info_label.text = 'Stoppet'
                except Exception as e:
                    log(f"stop_ambient error: {e}")

    # Helper for async prepare callback
    if USE_JNIUS:
        from jnius import PythonJavaClass, java_method
        class _PreparedListener(PythonJavaClass):
            __javainterfaces__ = ['android/media/MediaPlayer$OnPreparedListener']
            def __init__(self, mp):
                super().__init__()
                self._mp = mp
            @java_method('(Landroid/media/MediaPlayer;)V')
            def onPrepared(self, mp):
                self._mp.start()
    else:
        class _PreparedListener:
            def __init__(self, mp):
                pass

    # ============================================================
    # VERKTØY-FANEN
    # ============================================================
    class ToolsTab(ScrollView):
        def __init__(self, characters, **kwargs):
            super().__init__(**kwargs)
            self.characters = characters

            self.main_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None,
                                         padding=dp(10))
            self.main_layout.bind(minimum_height=self.main_layout.setter('height'))
            self.add_widget(self.main_layout)
            self.build_tools()

        def build_tools(self):
            header = Label(
                text='🎲 Verktøy',
                size_hint_y=None,
                height=dp(40),
                color=GOLD,
                font_size=sp(18),
                bold=True
            )
            self.main_layout.add_widget(header)

            # --- D20 Roller ---
            d20_label = Label(text='D20 Roller', size_hint_y=None, height=dp(30), color=GOLD, bold=True)
            self.main_layout.add_widget(d20_label)

            d20_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            self.d20_bonus = TextInput(text='0', multiline=False, size_hint_x=0.2,
                                       input_filter='int')
            d20_btn = RBtn(
                text='Roll D20',
                size_hint_x=0.8,
                bg_color=SMRG,
                hover_color=SMRG_DIM,
                shadow_color=SHAD,
                radius=dp(8)
            )
            d20_btn.bind(on_press=self.roll_d20)
            d20_layout.add_widget(self.d20_bonus)
            d20_layout.add_widget(d20_btn)
            self.main_layout.add_widget(d20_layout)

            self.d20_result = Label(
                text='',
                size_hint_y=None,
                height=dp(40),
                color=GOLD,
                font_size=sp(14),
                bold=True,
                markup=True
            )
            self.main_layout.add_widget(self.d20_result)

            # --- Flerterning ---
            dice_label = Label(text='Terning (f.eks 2d6+3)', size_hint_y=None, height=dp(30),
                               color=GOLD, bold=True)
            self.main_layout.add_widget(dice_label)

            dice_layout = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            self.dice_input = TextInput(text='1d20', multiline=False, size_hint_x=0.5)
            dice_btn = RBtn(
                text='Roll',
                size_hint_x=0.5,
                bg_color=BLUE,
                hover_color=[0.45, 0.65, 0.95, 1],
                shadow_color=SHAD,
                radius=dp(8)
            )
            dice_btn.bind(on_press=self.roll_dice)
            dice_layout.add_widget(self.dice_input)
            dice_layout.add_widget(dice_btn)
            self.main_layout.add_widget(dice_layout)

            self.dice_result = Label(
                text='',
                size_hint_y=None,
                height=dp(60),
                color=DIM,
                font_size=sp(12),
                markup=True
            )
            self.main_layout.add_widget(self.dice_result)

            # --- Initiative Tracker ---
            init_label = Label(text='Initiative Tracker', size_hint_y=None, height=dp(30),
                               color=GOLD, bold=True)
            self.main_layout.add_widget(init_label)

            self.initiative_container = BoxLayout(orientation='vertical', size_hint_y=None,
                                                   spacing=dp(5))
            self.initiative_container.bind(
                minimum_height=self.initiative_container.setter('height'))
            self.main_layout.add_widget(self.initiative_container)

            init_btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
            add_init_btn = RBtn(
                text='+ Legg til',
                size_hint_x=0.5,
                bg_color=GRN,
                hover_color=[0.4, 0.75, 0.45, 1],
                shadow_color=SHAD,
                radius=dp(8)
            )
            add_init_btn.bind(on_press=self.add_initiative_row)

            sort_init_btn = RBtn(
                text='Sorter',
                size_hint_x=0.5,
                bg_color=BLUE,
                hover_color=[0.45, 0.65, 0.95, 1],
                shadow_color=SHAD,
                radius=dp(8)
            )
            sort_init_btn.bind(on_press=self.sort_initiative)

            init_btn_row.add_widget(add_init_btn)
            init_btn_row.add_widget(sort_init_btn)
            self.main_layout.add_widget(init_btn_row)

        def roll_d20(self, *args):
            try:
                bonus = int(self.d20_bonus.text)
            except:
                bonus = 0
            result = D20Roller.roll_d20(bonus)
            nat = result - bonus
            if nat == 20:
                self.d20_result.text = f'[b]{result}[/b]  (NAT 20!)'
                self.d20_result.color = GOLD
            elif nat == 1:
                self.d20_result.text = f'[b]{result}[/b]  (NAT 1...)'
                self.d20_result.color = RED
            else:
                self.d20_result.text = f'[b]{result}[/b]'
                self.d20_result.color = TXT

        def roll_dice(self, *args):
            result = D20Roller.roll_dice(self.dice_input.text)
            if result:
                rolls_str = ', '.join(map(str, result['rolls']))
                bonus_str = f" + {result['bonus']}" if result['bonus'] > 0 else ""
                self.dice_result.text = f"[{rolls_str}]{bonus_str} = [b]{result['total']}[/b]"
            else:
                self.dice_result.text = 'Format: XdY eller XdY+Z (f.eks 2d6+3)'

        def add_initiative_row(self, *args):
            row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(5))
            name = TextInput(text='', multiline=False, hint_text='Navn', size_hint_x=0.4)
            init_val = TextInput(text='', multiline=False, hint_text='Init', size_hint_x=0.3,
                                 input_filter='int')
            roll_btn = RBtn(
                text='Roll',
                size_hint_x=0.3,
                bg_color=BLUE,
                hover_color=[0.45, 0.65, 0.95, 1],
                shadow_color=SHAD,
                radius=dp(5)
            )
            roll_btn.bind(on_press=partial(self.roll_initiative, name, init_val))
            row.add_widget(name)
            row.add_widget(init_val)
            row.add_widget(roll_btn)
            self.initiative_container.add_widget(row)

        def roll_initiative(self, name_input, init_input, *args):
            try:
                dex_mod = int(init_input.text) if init_input.text else 0
                result = random.randint(1, 20) + dex_mod
                init_input.text = str(result)
            except Exception as e:
                log(f"roll_initiative error: {e}")

        def sort_initiative(self, *args):
            rows = list(self.initiative_container.children[:])
            def get_init(row):
                try:
                    return int(row.children[1].text)
                except:
                    return -1
            rows.sort(key=get_init, reverse=True)
            self.initiative_container.clear_widgets()
            for row in rows:
                self.initiative_container.add_widget(row)

    # ============================================================
    # KARAKTERER-FANEN
    # ============================================================
    class CharacterTab(ScrollView):
        def __init__(self, characters, app_instance, **kwargs):
            super().__init__(**kwargs)
            self.characters = characters
            self.app_instance = app_instance

            self.main_layout = BoxLayout(orientation='vertical', spacing=dp(10), size_hint_y=None,
                                         padding=dp(10))
            self.main_layout.bind(minimum_height=self.main_layout.setter('height'))
            self.add_widget(self.main_layout)
            self.build_cast()

        def build_cast(self):
            header = Label(
                text='👥 Karakterer',
                size_hint_y=None,
                height=dp(40),
                color=GOLD,
                font_size=sp(18),
                bold=True
            )
            self.main_layout.add_widget(header)

            if self.characters:
                for name, char in self.characters.items():
                    char_btn = RBtn(
                        text=f'{char.name} ({char.class_name} lv{char.level})',
                        size_hint_y=None,
                        height=dp(50),
                        bg_color=BTN,
                        hover_color=SMRG_DIM,
                        shadow_color=SHAD,
                        radius=dp(8)
                    )
                    char_btn.bind(on_press=partial(self.show_character, name))
                    self.main_layout.add_widget(char_btn)

            new_btn = RBtn(
                text='+ Ny karakter',
                size_hint_y=None,
                height=dp(50),
                bg_color=SMRG,
                hover_color=SMRG_DIM,
                shadow_color=SHAD,
                radius=dp(8)
            )
            new_btn.bind(on_press=self.create_new_character)
            self.main_layout.add_widget(new_btn)

        def show_character(self, name, *args):
            try:
                char = self.characters[name]
                log(f"View character: {name}")

                detail_scroll = ScrollView()
                detail_layout = BoxLayout(orientation='vertical', spacing=dp(10),
                                          padding=dp(10), size_hint_y=None)
                detail_layout.bind(minimum_height=detail_layout.setter('height'))

                title = Label(
                    text=f'{char.name}',
                    size_hint_y=None,
                    height=dp(40),
                    color=GOLD,
                    font_size=sp(18),
                    bold=True
                )
                detail_layout.add_widget(title)

                subtitle = Label(
                    text=f'{char.race} {char.class_name} (Level {char.level})',
                    size_hint_y=None,
                    height=dp(30),
                    color=DIM,
                    font_size=sp(13)
                )
                detail_layout.add_widget(subtitle)

                # Ability scores
                abilities_label = Label(text='Ability Scores', size_hint_y=None, height=dp(30),
                                        color=GOLD, bold=True)
                detail_layout.add_widget(abilities_label)

                for ab in ['str','dex','con','int','wis','cha']:
                    score = getattr(char, ab, 10)
                    mod = char.get_modifier(ab)
                    row = BoxLayout(size_hint_y=None, height=dp(35), spacing=dp(5))
                    lbl = Label(text=f'{ab.upper()}: {score} ({mod:+d})', color=TXT,
                                font_size=sp(13), halign='left', text_size=(dp(200), None))
                    row.add_widget(lbl)
                    detail_layout.add_widget(row)

                # Combat stats
                combat_label = Label(text='Combat', size_hint_y=None, height=dp(30),
                                      color=GOLD, bold=True)
                detail_layout.add_widget(combat_label)

                hp_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(10))
                hp_lbl = Label(text=f'HP: {char.hp_current}/{char.hp_max}', color=TXT,
                               size_hint_x=0.4, font_size=sp(13))
                hp_minus = RBtn(text='-', size_hint_x=0.15, bg_color=RED,
                                hover_color=[1, 0.4, 0.4, 1], shadow_color=SHAD, radius=dp(5))
                hp_plus = RBtn(text='+', size_hint_x=0.15, bg_color=GRN,
                               hover_color=[0.4, 0.75, 0.45, 1], shadow_color=SHAD, radius=dp(5))
                hp_amt = TextInput(text='1', multiline=False, size_hint_x=0.3,
                                   input_filter='int')

                def change_hp(delta, *a):
                    try:
                        amt = int(hp_amt.text) if hp_amt.text else 1
                        char.hp_current = max(0, min(char.hp_max, char.hp_current + delta * amt))
                        hp_lbl.text = f'HP: {char.hp_current}/{char.hp_max}'
                        save_characters(self.characters)
                    except:
                        pass

                hp_minus.bind(on_press=partial(change_hp, -1))
                hp_plus.bind(on_press=partial(change_hp, 1))
                hp_row.add_widget(hp_lbl)
                hp_row.add_widget(hp_minus)
                hp_row.add_widget(hp_amt)
                hp_row.add_widget(hp_plus)
                detail_layout.add_widget(hp_row)

                ac_lbl = Label(text=f'AC: {char.ac}  |  Speed: {char.speed} ft',
                               size_hint_y=None, height=dp(30), color=TXT, font_size=sp(13))
                detail_layout.add_widget(ac_lbl)

                # Close button
                close_btn = RBtn(
                    text='← Tilbake',
                    size_hint_y=None,
                    height=dp(50),
                    bg_color=BTN,
                    hover_color=BTNH,
                    shadow_color=SHAD,
                    radius=dp(8)
                )
                close_btn.bind(on_press=lambda x: self.close_detail())
                detail_layout.add_widget(close_btn)

                detail_scroll.add_widget(detail_layout)
                self.app_instance.content_area.clear_widgets()
                self.app_instance.content_area.add_widget(detail_scroll)

            except Exception as e:
                log(f"show_character error: {e}")

        def close_detail(self):
            self.main_layout.clear_widgets()
            self.build_cast()
            self.app_instance.content_area.clear_widgets()
            self.app_instance.content_area.add_widget(self)

        def create_new_character(self, *args):
            new_char = D20Character(f"Karakter {len(self.characters) + 1}")
            self.characters[new_char.name] = new_char
            save_characters(self.characters)
            self.main_layout.clear_widgets()
            self.build_cast()

    # ============================================================
    # CHROMECAST
    # ============================================================
    class CastScreen(BoxLayout):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            self.orientation = 'vertical'
            self.spacing = dp(10)
            self.padding = dp(10)

            header = Label(
                text='📺 Chromecast',
                size_hint_y=None,
                height=dp(40),
                color=GOLD,
                font_size=sp(18),
                bold=True
            )
            self.add_widget(header)

            if CAST_AVAILABLE:
                discover_btn = RBtn(
                    text='Søk etter enheter',
                    size_hint_y=None,
                    height=dp(50),
                    bg_color=SMRG,
                    hover_color=SMRG_DIM,
                    shadow_color=SHAD,
                    radius=dp(8)
                )
                discover_btn.bind(on_press=self.discover_devices)
                self.add_widget(discover_btn)

                self.status_label = Label(
                    text='Ingen enheter oppdaget',
                    size_hint_y=None,
                    height=dp(40),
                    color=DIM
                )
                self.add_widget(self.status_label)
            else:
                no_cast = Label(
                    text='pychromecast ikke installert',
                    color=RED
                )
                self.add_widget(no_cast)

        def discover_devices(self, *args):
            self.status_label.text = 'Søker...'
            if CAST_AVAILABLE:
                try:
                    services, browser = pychromecast.discover_listed_mdns_services()
                    if services:
                        self.status_label.text = f'{len(services)} enheter funnet'
                except Exception as e:
                    log(f"discover_devices error: {e}")
                    self.status_label.text = f'Feil: {e}'

    # ============================================================
    # MAIN APP
    # ============================================================
    class CampaignForgeApp(App):
        def build(self):
            Window.clearcolor = BG
            ensure_dirs()

            self.characters = load_characters()
            if not self.characters:
                self.characters['Eksempel'] = D20Character('Eksempel')

            main_box = BoxLayout(orientation='vertical')

            # Content area FØRST (tar opp plassen)
            self.content_area = BoxLayout()
            main_box.add_widget(self.content_area)

            # Tab-bar SIST (havner nederst)
            tab_box = BoxLayout(size_hint_y=None, height=dp(52), spacing=dp(2),
                                padding=[dp(4), dp(4), dp(4), dp(4)])

            tab_names = ['Bilder', 'Musikk', 'Ambient', 'Verktøy', 'Chars', 'Cast']
            self.first_tab_btn = None

            for tab_name in tab_names:
                btn = ToggleButton(
                    text=tab_name,
                    size_hint_x=1.0 / len(tab_names),
                    background_normal='',
                    background_down='',
                    background_color=[0, 0, 0, 0],
                    color=GOLD if tab_name == 'Bilder' else DIM,
                    group='tabs',
                    bold=True,
                    font_size=sp(12)
                )
                btn.bind(state=partial(self.switch_tab, tab_name, btn))
                if tab_name == 'Bilder':
                    self.first_tab_btn = btn
                tab_box.add_widget(btn)

            main_box.add_widget(tab_box)

            # Sett første tab
            if self.first_tab_btn:
                self.first_tab_btn.state = 'down'

            return main_box

        def switch_tab(self, tab_name, btn, instance, state):
            if state == 'down':
                # Oppdater tab-farger
                for child in btn.parent.children:
                    child.color = DIM
                btn.color = GOLD

                self.content_area.clear_widgets()

                if tab_name == 'Bilder':
                    self.content_area.add_widget(ImageGallery())
                elif tab_name == 'Musikk':
                    self.content_area.add_widget(MusicPlayer())
                elif tab_name == 'Ambient':
                    self.content_area.add_widget(AmbientSounds())
                elif tab_name == 'Verktøy':
                    self.content_area.add_widget(ToolsTab(self.characters))
                elif tab_name == 'Chars':
                    self.content_area.add_widget(CharacterTab(self.characters, self))
                elif tab_name == 'Cast':
                    self.content_area.add_widget(CastScreen())

        def on_pause(self):
            save_characters(self.characters)
            return True

        def on_resume(self):
            pass

    log("Building app...")
    app = CampaignForgeApp()
    app.run()

except Exception as e:
    log(f"FATAL ERROR: {e}")
    log(traceback.format_exc())
    raise
