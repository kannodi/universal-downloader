"""
Universal Downloader - Configuration Module
Handles user preferences persistence using JSON.
"""

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, Optional

# Default configuration values
DEFAULTS = {
    "last_download_path": str(Path.home() / "Downloads"),
    "default_video_format": "mp4",
    "default_audio_format": "mp3",
    "default_video_quality": "1080p",
    "default_audio_quality": "320kbps",
    "last_video_format": "mp4",
    "last_audio_format": "mp3",
    "last_video_quality": "1080p",
    "last_audio_quality": "320kbps",
    "download_type": "video",
    "remember_location": True,
    "theme": "dark",
    "check_updates_on_start": True,
    "always_on_top": False,
    "desktop_destination": False,
    "copy_to_clipboard": False,
    "mute_video": False,
    "browser_cookies": "none"
}

class Config:
    """Configuration manager for the application."""

    def __init__(self, config_dir: Optional[Path] = None):
        # Config file in user's app data
        self.config_dir = Path(config_dir) if config_dir is not None else Path.home() / ".universal_downloader"
        self.config_file = self.config_dir / "config.json"
        self._config = {}
        self._lock = threading.RLock()
        self._load()

    def _load(self) -> None:
        """Load configuration from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    self._config = {**DEFAULTS, **loaded} if isinstance(loaded, dict) else DEFAULTS.copy()
            except (json.JSONDecodeError, UnicodeDecodeError, IOError):
                self._config = DEFAULTS.copy()
        else:
            self._config = DEFAULTS.copy()

    def _save(self) -> None:
        """Save configuration to JSON file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8',
                                             dir=self.config_dir, delete=False) as f:
                temp_path = Path(f.name)
                json.dump(self._config, f, indent=2, ensure_ascii=False)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temp_path, self.config_file)
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, DEFAULTS.get(key, default))

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save."""
        with self._lock:
            self._config[key] = value
            self._save()

    def get_download_path(self) -> str:
        """Get the last used download path."""
        path = self.get("last_download_path")
        if path and os.path.isdir(path):
            return path
        return str(Path.home() / "Downloads")

    def set_download_path(self, path: str) -> None:
        """Set the download path if 'remember location' is enabled."""
        if self.get("remember_location", True):
            self.set("last_download_path", path)

    def reset(self) -> None:
        """Reset to default configuration."""
        with self._lock:
            self._config = DEFAULTS.copy()
            self._save()


# Singleton instance
config = Config()
