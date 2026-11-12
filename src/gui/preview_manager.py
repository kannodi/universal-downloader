try:
    import pygame
    PYGAME_LOADED = True
except ImportError:
    PYGAME_LOADED = False

class PreviewPlayer:
    """Manages audio playback for previews using pygame."""

    def __init__(self):
        self._preview_playing = False
        self._is_paused = False
        self._preview_file = None
        self._playback_start_offset = 0

    @property
    def is_playing(self):
        return self._preview_playing

    @property
    def is_paused(self):
        return self._is_paused

    @property
    def has_file(self):
        return self._preview_file is not None

    def load_file(self, filepath):
        self._preview_file = filepath

    def play(self, offset=0):
        if not PYGAME_LOADED or not self._preview_file:
            return False
        try:
            self._playback_start_offset = offset
            pygame.mixer.music.load(self._preview_file)
            pygame.mixer.music.play(start=self._playback_start_offset)
            self._preview_playing = True
            self._is_paused = False
            return True
        except Exception as e:
            print(f"Error starting playback: {e}")
            return False

    def toggle(self):
        if not PYGAME_LOADED or not self._preview_file:
            return False

        if self._preview_playing:
            pygame.mixer.music.pause()
            self._preview_playing = False
            self._is_paused = True
        else:
            try:
                if self._is_paused:
                    pygame.mixer.music.unpause()
                else:
                    pygame.mixer.music.play(start=self._playback_start_offset)
            except:
                pygame.mixer.music.load(self._preview_file)
                pygame.mixer.music.play(start=self._playback_start_offset)
            self._preview_playing = True
            self._is_paused = False
        return True

    def stop(self):
        if PYGAME_LOADED:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except: pass
        self._preview_playing = False
        self._is_paused = False
        self._preview_file = None
        self._playback_start_offset = 0

    def get_position(self):
        if not PYGAME_LOADED or not self._preview_playing:
            return -1
        if not pygame.mixer.music.get_busy() and self._preview_playing:
            self._preview_playing = False
            self._is_paused = False
            return -2 # Finished
        return pygame.mixer.music.get_pos()

    def seek(self, offset):
        if not PYGAME_LOADED or not self._preview_file:
            return
        self._playback_start_offset = offset
        try:
            pygame.mixer.music.play(start=offset)
            if not self._preview_playing:
                pygame.mixer.music.pause()
        except:
            pass
