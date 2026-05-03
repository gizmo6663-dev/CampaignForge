"""CampaignForge – lyd-lag for scenarier.

LayerPlayer: én MediaPlayer-instans per loop-boks i en scene.
Flere kan kjøre parallelt, hver med eget volum. Looper.

OneShotPlayer: fyrer av korte SFX. Hver avfyring lager egen
MediaPlayer som ryddes opp automatisk når lyden er ferdig.
Tillater overlappende oneshots.
"""
import os, threading

from kivy.clock import Clock
from cf_common import USE_JNIUS, MediaPlayer, log


class LayerPlayer:
    """Looper én lydkilde (lokal fil eller URL) med eget volum."""

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
                    try:
                        mp.setLooping(loop)
                    except Exception:
                        pass
                    mp.prepare()
                    mp.start()
                    self.mp = mp
                    self.is_playing = True
                    log(f"Layer OK: {source[:60]}")
                except Exception as e:
                    log(f"Layer err: {e}")
                    self.is_playing = False
            # URLer trenger thread; lokale filer er raskt – men gjør det
            # likt for konsistens.
            threading.Thread(target=_s, daemon=True).start()
            return True
        # Fallback (desktop): Kivy SoundLoader, kun lokale filer
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
                    except Exception:
                        pass
                    try:
                        self.mp.release()
                    except Exception:
                        pass
                else:
                    try:
                        self.mp.stop()
                    except Exception:
                        pass
            except Exception:
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
        except Exception:
            pass

    def fade_out(self, duration=2.0):
        """Fade volumet til 0 over `duration` sekunder, så stopp.

        Brukes ved scene-overganger så lyder ikke kuttes brått.
        """
        if not self.mp or not self.is_playing:
            self.stop()
            return
        steps = max(1, int(duration * 20))   # 20 fps
        step_dt = duration / steps
        start_v = self._v
        counter = [0]

        def _tick(dt):
            counter[0] += 1
            if counter[0] >= steps or not self.mp:
                self.stop()
                return False
            new_v = start_v * (1.0 - counter[0] / steps)
            try:
                if USE_JNIUS:
                    self.mp.setVolume(new_v, new_v)
                else:
                    self.mp.volume = new_v
            except Exception:
                pass
            return True

        Clock.schedule_interval(_tick, step_dt)


class OneShotPlayer:
    """Fyrer av korte lyder med automatisk opprydding etter avspilling."""

    def __init__(self):
        self._players = []          # aktive Android MediaPlayer
        self._snds = []             # aktive Kivy Sound (fallback)
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
        for p in self._players[:]:
            try:
                if not p.isPlaying():
                    try:
                        p.release()
                    except Exception:
                        pass
                    self._players.remove(p)
            except Exception:
                try:
                    self._players.remove(p)
                except Exception:
                    pass
        for s in self._snds[:]:
            try:
                if s.state != 'play':
                    self._snds.remove(s)
            except Exception:
                try:
                    self._snds.remove(s)
                except Exception:
                    pass
        if not self._players and not self._snds:
            self._cleanup_running = False
            return False
        return True

    def stop_all(self):
        for p in self._players[:]:
            try:
                if p.isPlaying():
                    p.stop()
                p.release()
            except Exception:
                pass
        self._players.clear()
        for s in self._snds[:]:
            try:
                s.stop()
            except Exception:
                pass
        self._snds.clear()

    def vol(self, v):
        self._v = v
