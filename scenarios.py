"""CampaignForge – scenario-funksjonalitet (Lyd-fanens Scenarier-undertab).

Dette er et MIXIN: legg det på CampaignForgeApp slik:
    class CampaignForgeApp(App, ScenariosMixin):
        ...

Mixinet tilbyr alle _scn_*, _mk_scn_*, _show_loop_editor og
_show_oneshot_editor-metoder, samt selve Lyd-fanens dispatcher
(_mk_lyd og dens sub-tabs Musikk/Ambient/One-shot/Scenarier).

Forutsetter at appen har følgende attributter (initialisert i build()):
    self.player        – musikkspiller (APlayer/FPlayer)
    self.streamer      – ambient-streamer (SPlayer)
    self.oneshot       – OneShotPlayer
    self.scenarios     – liste lastet fra SCENARIO_FILE
    self.library       – liste lastet fra LIBRARY_FILE
    self._scn_view     – 'list' | 'scenes' | 'editor'
    self._scn_idx      – aktivt scenario-index (eller None)
    self._scn_scene_idx – aktiv scene-index (eller None)
    self._scn_layers   – liste av aktive LayerPlayer
    self._scn_perf_mode – bool, om performance-modus er på
    self.root          – Kivy widget-root (FloatLayout for overlays)
"""
import os, copy

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.uix.floatlayout import FloatLayout
from kivy.metrics import dp, sp
from kivy.clock import Clock

from cf_common import (
    BG, BG2, INPUT, BTN, BTNH, GOLD, GDIM, TXT, DIM, RED,
    LOOP_BG, LOOP_BG_ON, ONE_BG, ONE_BORDER,
    SND_EXT, MUSIC_DIR, ONESHOT_DIR,
    SCENARIO_FILE, LIBRARY_FILE,
    AMBIENT_SOUNDS, VOGLER_STAGES,
    RBtn, RToggle, RBox, FramedBox,
    mkbtn, mklbl, mkvol, mksep,
    save_json, load_json, log,
)
from audio_layers import LayerPlayer


class ScenariosMixin:
    """Scenario-bygger og avspiller. Mixin på CampaignForgeApp."""

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
                row = BoxLayout(size_hint_y=None, height=dp(52),
                                spacing=dp(6))
                name = sc.get('name', f'Scenario {i+1}')
                n_scenes = len(sc.get('scenes', []))
                row.add_widget(mkbtn(
                    f"{name}  ({n_scenes} scener)",
                    lambda idx=i: self._scn_open(idx)))
                row.add_widget(mkbtn("Endre", lambda idx=i:
                                     self._scn_rename(idx),
                                     small=True,
                                     size_hint_x=None, width=dp(70)))
                row.add_widget(mkbtn("X", lambda idx=i:
                                     self._scn_delete(idx),
                                     danger=True, small=True,
                                     size_hint_x=None, width=dp(46)))
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
                        for j in range(3)
                    ],
                    'oneshot_boxes': [
                        {'label': f'SFX {j+1}', 'src': None,
                         'volume': 0.8}
                        for j in range(2)
                    ],
                })
            self.scenarios.append({
                'name': name,
                'scenes': scenes,
                'master_volume': 1.0,
                'last_scene_idx': 0,
            })
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
        """Åpne scenario direkte i editor for sist åpnede scene.
    
        Hvis scenarioet ikke har scener, vis scenelisten istedenfor.
        """
        self._scn_stop_all()
        self._scn_idx = idx
        sc = self.scenarios[idx]
        scenes = sc.get('scenes', [])
        if scenes:
            last = sc.get('last_scene_idx', 0)
            if last < 0 or last >= len(scenes):
                last = 0
            self._scn_scene_idx = last
            self._scn_view = 'editor'
        else:
            # Tomt scenario → må til scenelisten for å legge til
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
                row = BoxLayout(size_hint_y=None, height=dp(52),
                                spacing=dp(4))
                # Tell konfigurerte bokser for å gi rask oversikt
                loops = sn.get('loop_boxes', [])
                oneshots = sn.get('oneshot_boxes', [])
                n_loop_set = sum(1 for b in loops if b.get('src'))
                n_one_set = sum(1 for b in oneshots if b.get('src'))
                label = (f"{i+1}. {sn.get('name','?')}\n"
                         f"   Lag {n_loop_set}/{len(loops)}  "
                         f"SFX {n_one_set}/{len(oneshots)}")
                row.add_widget(mkbtn(label,
                    lambda idx=i: self._scn_open_scene(idx)))
                row.add_widget(mkbtn("^",
                    lambda idx=i: self._scn_move_scene(idx, -1),
                    small=True, size_hint_x=None, width=dp(36)))
                row.add_widget(mkbtn("v",
                    lambda idx=i: self._scn_move_scene(idx, 1),
                    small=True, size_hint_x=None, width=dp(36)))
                row.add_widget(mkbtn("Endre",
                    lambda idx=i: self._scn_rename_scene(idx),
                    small=True, size_hint_x=None, width=dp(64)))
                row.add_widget(mkbtn("X",
                    lambda idx=i: self._scn_delete_scene(idx),
                    danger=True, small=True,
                    size_hint_x=None, width=dp(40)))
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
                    for j in range(3)
                ],
                'oneshot_boxes': [
                    {'label': f'SFX {j+1}', 'src': None,
                     'volume': 0.8}
                    for j in range(2)
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
        p = BoxLayout(orientation='vertical', spacing=dp(8),
                      padding=dp(4))
        sc = self.scenarios[self._scn_idx]
        scenes = sc['scenes']
        n_scenes = len(scenes)
        sn = scenes[self._scn_scene_idx]
        self._scn_box_widgets = []
    
        # Header med tilbake-knapp og forrige/neste-piler
        top = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        top.add_widget(mkbtn("<", self._scn_back_to_list,
                             small=True, size_hint_x=None, width=dp(40)))
        # Forrige scene
        prev_disabled = self._scn_scene_idx <= 0
        prev_btn = mkbtn("<<",
            lambda: self._scn_goto_scene(self._scn_scene_idx - 1),
            small=True, size_hint_x=None, width=dp(48))
        if prev_disabled:
            prev_btn.disabled = True
            prev_btn.opacity = 0.35
        top.add_widget(prev_btn)
        # Tittel midten
        title_lbl = mklbl(
            f"{self._scn_scene_idx + 1}/{n_scenes}  {sn.get('name','?')}",
            color=GOLD, size=13, bold=True)
        top.add_widget(title_lbl)
        # Neste scene
        next_disabled = self._scn_scene_idx >= n_scenes - 1
        next_btn = mkbtn(">>",
            lambda: self._scn_goto_scene(self._scn_scene_idx + 1),
            small=True, size_hint_x=None, width=dp(48))
        if next_disabled:
            next_btn.disabled = True
            next_btn.opacity = 0.35
        top.add_widget(next_btn)
        p.add_widget(top)
    
        perf = getattr(self, '_scn_perf_mode', False)
    
        # Loop-bokser overskrift + +/- knapper (kun i edit-modus)
        loop_hdr = BoxLayout(size_hint_y=None, height=dp(38),
                             spacing=dp(6))
        loop_hdr.add_widget(mklbl("Lag (loop)", color=GDIM, size=11,
                                  bold=True))
        if not perf:
            loop_hdr.add_widget(mkbtn("+ Boks",
                lambda: self._scn_add_box('loop'),
                small=True, size_hint_x=None, width=dp(86)))
            loop_hdr.add_widget(mkbtn("− Boks",
                lambda: self._scn_remove_box('loop'),
                danger=True, small=True,
                size_hint_x=None, width=dp(86)))
        p.add_widget(loop_hdr)
    
        # Loop-grid (2 kolonner)
        loop_scroll = ScrollView(size_hint_y=0.55)
        loop_grid = GridLayout(cols=2, spacing=dp(8), padding=dp(4),
                               size_hint_y=None)
        loop_grid.bind(minimum_height=loop_grid.setter('height'))
        for i, box in enumerate(sn.get('loop_boxes', [])):
            w = self._mk_loop_box_face(i, box)
            loop_grid.add_widget(w)
        loop_scroll.add_widget(loop_grid)
        p.add_widget(loop_scroll)
    
        # One-shot overskrift + +/- (kun i edit-modus)
        os_hdr = BoxLayout(size_hint_y=None, height=dp(38), spacing=dp(6))
        os_hdr.add_widget(mklbl("One-shots", color=GDIM, size=11,
                                bold=True))
        if not perf:
            os_hdr.add_widget(mkbtn("+",
                lambda: self._scn_add_box('one'),
                small=True, size_hint_x=None, width=dp(56)))
            os_hdr.add_widget(mkbtn("−",
                lambda: self._scn_remove_box('one'),
                danger=True, small=True,
                size_hint_x=None, width=dp(56)))
        p.add_widget(os_hdr)
    
        # One-shot-rad (horisontal scroll) – større bokser
        os_scroll = ScrollView(size_hint_y=None, height=dp(96),
                               do_scroll_x=True, do_scroll_y=False)
        os_row = BoxLayout(orientation='horizontal',
                           size_hint_x=None,
                           spacing=dp(8), padding=dp(4))
        os_row.bind(minimum_width=os_row.setter('width'))
        for i, box in enumerate(sn.get('oneshot_boxes', [])):
            w = self._mk_oneshot_box_face(i, box)
            os_row.add_widget(w)
        os_scroll.add_widget(os_row)
        p.add_widget(os_scroll)
    
        # === MASTER-VOLUM ===
        mv_row = BoxLayout(size_hint_y=None, height=dp(36),
                           spacing=dp(8), padding=[dp(4), 0])
        mv_row.add_widget(mklbl("Master:", color=DIM, size=11, h=20))
        master_sl = Slider(
            min=0, max=1,
            value=sc.get('master_volume', 1.0),
            size_hint_x=1)
        # Sett scenarioets master, oppdater alle aktive lag i sanntid
        master_sl.bind(value=lambda s, v: self._scn_set_master(v))
        mv_row.add_widget(master_sl)
        p.add_widget(mv_row)
    
        # === FOOTER-KONTROLLER ===
        # Rad 1: hovedhandlinger
        foot1 = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(6))
        foot1.add_widget(mkbtn("Spill alle",
            self._scn_play_all_loops, accent=True))
        foot1.add_widget(mkbtn("Stopp alle",
            self._scn_stop_all, danger=True))
        p.add_widget(foot1)
    
        # Rad 2: navigasjon/management
        foot2 = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
        foot2.add_widget(mkbtn("Scener",
            self._scn_back_to_scenes, small=True))
        if not perf:
            foot2.add_widget(mkbtn("Dupliser scene",
                self._scn_duplicate_current, small=True))
        foot2.add_widget(mkbtn(
            "Spillemodus" if not perf else "Edit-modus",
            self._scn_toggle_perf, small=True,
            accent=perf))
        p.add_widget(foot2)
    
        return p
    
    def _scn_set_master(self, v):
        """Lagre master-volum og juster alle aktive lag i sanntid."""
        sc = self.scenarios[self._scn_idx]
        sc['master_volume'] = v
        for i, lp in enumerate(self._scn_layers):
            if lp and lp.is_playing:
                sn = sc['scenes'][self._scn_scene_idx]
                if i < len(sn.get('loop_boxes', [])):
                    box_v = sn['loop_boxes'][i].get('volume', 0.7)
                    lp.vol(box_v * v)
        # Lagring bruker debounce ved å skje i on_stop, men vi tar
        # det med en gang så ingenting forsvinner ved krasj
        save_json(SCENARIO_FILE, self.scenarios)
    
    def _scn_duplicate_current(self):
        """Lag en kopi av nåværende scene rett etter den i lista."""
        import copy
        sc = self.scenarios[self._scn_idx]
        cur_idx = self._scn_scene_idx
        new_scene = copy.deepcopy(sc['scenes'][cur_idx])
        new_scene['name'] = new_scene.get('name', 'Scene') + ' (kopi)'
        sc['scenes'].insert(cur_idx + 1, new_scene)
        save_json(SCENARIO_FILE, self.scenarios)
        # Hopp til den nye kopien
        self._scn_stop_all()
        self._scn_scene_idx = cur_idx + 1
        sc['last_scene_idx'] = self._scn_scene_idx
        self._scn_refresh()
        self._toast(f"Kopiert: {new_scene['name']}")
    
    def _scn_goto_scene(self, new_idx):
        """Naviger til en annen scene fra editor-toppen.
    
        Hvis lag spiller, fades de ut over 2 sekunder i stedet
        for å stoppe brått (behageligere overgang under spill).
        """
        sc = self.scenarios[self._scn_idx]
        if not (0 <= new_idx < len(sc['scenes'])):
            return
        # Sjekk om noe spiller
        any_playing = any(
            lp and lp.is_playing for lp in self._scn_layers
        )
        if any_playing:
            # Fade ut alle aktive lag, men la oneshots klinge ut
            for lp in self._scn_layers:
                if lp:
                    try: lp.fade_out(2.0)
                    except Exception: lp.stop()
            # Lagene rydder seg selv via fade_out → vi kan glemme refs
            self._scn_layers = []
        else:
            self._scn_stop_all()
        self._scn_scene_idx = new_idx
        sc['last_scene_idx'] = new_idx
        save_json(SCENARIO_FILE, self.scenarios)
        self._scn_refresh()
    
    def _mk_loop_box_face(self, idx, box):
        """Liten boks for et loop-lag i scene-editoren.

        I performance-modus skjules Endre-knappen og hele boksen blir
        en stor "Spill/Stopp"-trykkflate.
        """
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

        perf = getattr(self, '_scn_perf_mode', False)
        height = dp(132) if perf else dp(116)

        outer = RBox(orientation='vertical',
                     size_hint_y=None, height=height,
                     padding=dp(8), spacing=dp(4),
                     bg_color=bg, radius=dp(12))
        inner = BoxLayout(orientation='vertical', spacing=dp(3))

        top_lbl = Label(text=label, color=GOLD,
                        font_size=sp(13 if perf else 12),
                        bold=True, size_hint_y=None,
                        height=dp(24 if perf else 22),
                        halign='center')
        top_lbl.bind(size=top_lbl.setter('text_size'))
        inner.add_widget(top_lbl)

        sub_lbl = Label(text=sub_hint,
                        color=TXT if src else DIM,
                        font_size=sp(10),
                        size_hint_y=None, height=dp(20),
                        halign='center', shorten=True)
        sub_lbl.bind(size=sub_lbl.setter('text_size'))
        inner.add_widget(sub_lbl)

        if perf:
            # Performance-modus: én stor Spill/Stopp-knapp, ingen Endre
            play_txt = "STOPP" if playing else "SPILL"
            play_btn = mkbtn(play_txt,
                lambda i=idx: self._scn_toggle_layer(i),
                accent=playing, danger=playing)
            play_btn.font_size = sp(15)
            play_btn.bold = True
            inner.add_widget(play_btn)
        else:
            # Edit-modus: liten Spill + Endre-rad
            ctrl = BoxLayout(size_hint_y=None, height=dp(40),
                             spacing=dp(6))
            play_txt = "Stopp" if playing else "Spill"
            play_btn = mkbtn(play_txt,
                lambda i=idx: self._scn_toggle_layer(i),
                accent=playing, danger=playing)
            ctrl.add_widget(play_btn)
            edit_btn = mkbtn("Endre",
                lambda i=idx: self._scn_edit_loop_box(i))
            ctrl.add_widget(edit_btn)
            inner.add_widget(ctrl)

        outer.add_widget(inner)
        return outer

    def _mk_oneshot_box_face(self, idx, box):
        """Liten boks for en one-shot, mørkere farge med gull-ramme.

        I performance-modus blir hele boksen til én stor fyr-av-knapp.
        """
        label = box.get('label', f'SFX {idx+1}')
        src = box.get('src')
        perf = getattr(self, '_scn_perf_mode', False)
        width = dp(124) if perf else dp(112)

        # Wrapper gir gull-ramme via FramedBox
        wrap = FramedBox(orientation='vertical',
                         size_hint_x=None, width=width,
                         padding=dp(3), frame_color=ONE_BORDER)
        inner = RBox(orientation='vertical',
                     padding=dp(5), spacing=dp(3),
                     bg_color=ONE_BG, radius=dp(8))

        if perf:
            # Performance-modus: én stor knapp
            fire = mkbtn(label,
                lambda i=idx: self._scn_fire_oneshot(i),
                accent=True)
            fire.font_size = sp(13)
            fire.bold = True
            if not src:
                fire.color = DIM
            inner.add_widget(fire)
        else:
            # Edit-modus: knapp + Endre under
            fire = mkbtn(label,
                lambda i=idx: self._scn_fire_oneshot(i),
                accent=True, size_hint_y=0.66)
            if not src:
                fire.color = DIM
            inner.add_widget(fire)
            edit = mkbtn("Endre",
                lambda i=idx: self._scn_edit_oneshot_box(i),
                small=True, size_hint_y=0.34)
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
            # Effektivt volum = boks-volum * scenarioets master
            box_v = box.get('volume', 0.7)
            master = sc.get('master_volume', 1.0)
            lp._v = box_v * master
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
        master = sc.get('master_volume', 1.0)
        self._scn_ensure_layers_size(len(sn['loop_boxes']))
        for i, box in enumerate(sn['loop_boxes']):
            if not box.get('src') or not box.get('kind'):
                continue
            lp = self._scn_layers[i]
            if lp and lp.is_playing:
                continue
            lp = LayerPlayer()
            lp._v = box.get('volume', 0.7) * master
            if box['kind'] == 'ambient':
                lp.play(box['src'], is_url=True, loop=True)
            else:
                lp.play(box['src'], is_url=False, loop=True)
            self._scn_layers[i] = lp
        self._scn_refresh()
    
    def _scn_stop_all(self):
        """Stopp alle aktive lag-spillere OG one-shots."""
        for lp in self._scn_layers:
            if lp:
                try: lp.stop()
                except: pass
        self._scn_layers = []
        # Stopp også alle one-shots som kan være i etterklang
        try: self.oneshot.stop_all()
        except Exception as e: log(f"oneshot stop_all err: {e}")
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
        master = sc.get('master_volume', 1.0)
        old_v = self.oneshot._v
        self.oneshot._v = box.get('volume', 0.8) * master
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
                       ('local', 'Egne'), ('library', 'Bibliotek')]:
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

        def _select_from_lib(entry):
            """Last konfigurasjon fra bibliotek-entry inn i state."""
            state['kind'] = entry.get('kind')
            state['src'] = entry.get('src')
            state['volume'] = entry.get('volume', 0.7)
            # Oppdater navn-felt og volum-slider
            name_in.text = entry.get('label', '')
            vol_sl.value = state['volume']
            sel_lbl.text = f"Valgt: {self._lib_label_for_entry(entry)}"
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
            elif k == 'local':
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
            elif k == 'library':
                # "Lagre dette laget"-knapp øverst
                save_btn = mkbtn(
                    "+ Lagre nåværende lag i bibliotek",
                    lambda: (self._lib_save({
                        'label': name_in.text.strip() or
                                 f'Lag {box_idx+1}',
                        'kind': state['kind'],
                        'src': state['src'],
                        'volume': state['volume'],
                    }), _refresh_list()),
                    accent=True, size_hint_y=None, height=dp(40))
                list_grid.add_widget(save_btn)

                if not self.library:
                    list_grid.add_widget(mklbl(
                        "Biblioteket er tomt.\n\n"
                        "Konfigurer et lag (velg Musikk/Ambient/\n"
                        "Egne, sett volum), kom tilbake hit og\n"
                        "trykk + for å lagre det.",
                        color=DIM, size=10, h=100, wrap=True))
                else:
                    for li, entry in enumerate(self.library):
                        row = BoxLayout(size_hint_y=None, height=dp(40),
                                        spacing=dp(4))
                        row.add_widget(mkbtn(
                            self._lib_label_for_entry(entry),
                            lambda e=entry: _select_from_lib(e),
                            small=True))
                        row.add_widget(mkbtn(
                            "X",
                            lambda i=li: (
                                self._lib_delete(i),
                                _refresh_list()),
                            danger=True, small=True,
                            size_hint_x=None, width=dp(38)))
                        list_grid.add_widget(row)
    
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
                # Oppdater volum hvis lag spiller (med master)
                if box_idx < len(self._scn_layers):
                    lp = self._scn_layers[box_idx]
                    if lp:
                        sc_local = self.scenarios[self._scn_idx]
                        master = sc_local.get('master_volume', 1.0)
                        lp.vol(state['volume'] * master)
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

    # ============================================================
    # === NYE FEATURES: PERFORMANCE-MODUS + LAYER-BIBLIOTEK ======
    # ============================================================

    def _scn_toggle_perf(self):
        """Bytt mellom edit- og performance-modus i editoren.

        Performance-modus skjuler Endre-knapper, gjør play-knappene
        større, og reduserer visuell støy så DM kan navigere lyder
        raskt under selve spillet.
        """
        self._scn_perf_mode = not getattr(self, '_scn_perf_mode', False)
        self._scn_refresh()

    # ---------- LAYER-BIBLIOTEK ----------
    def _lib_save(self, entry):
        """Lagre en boks-konfig (label, kind, src, volume) til biblioteket."""
        if not entry.get('src') or not entry.get('kind'):
            self._toast("Kan ikke lagre tomt lag.")
            return
        # Ikke lagre duplikater (samme kind + src + label)
        for existing in self.library:
            if (existing.get('kind') == entry.get('kind') and
                    existing.get('src') == entry.get('src') and
                    existing.get('label') == entry.get('label')):
                self._toast("Allerede i biblioteket.")
                return
        self.library.append({
            'label': entry.get('label', '(uten navn)'),
            'kind': entry['kind'],
            'src': entry['src'],
            'volume': entry.get('volume', 0.7),
        })
        save_json(LIBRARY_FILE, self.library)
        self._toast(f"Lagret: {entry.get('label')}")

    def _lib_delete(self, idx, on_done=None):
        """Fjern en bibliotek-entry."""
        if 0 <= idx < len(self.library):
            self.library.pop(idx)
            save_json(LIBRARY_FILE, self.library)
            if on_done:
                on_done()

    def _lib_label_for_entry(self, entry):
        """Generer en kort visningsetikett for en bibliotek-entry."""
        kind = entry.get('kind', '?')
        src = entry.get('src', '')
        sub = (
            os.path.basename(src) if kind in ('music', 'local')
            else src if kind == 'ambient' else '?'
        )
        kind_lbl = {'music': 'M', 'ambient': 'A', 'local': 'L'}.get(kind, '?')
        return f"[{kind_lbl}] {entry.get('label', '?')} – {sub}"
