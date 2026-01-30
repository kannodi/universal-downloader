"""
Universal Downloader - Configuration Module
Handles user preferences persistence using JSON.
"""

import json
import os
from pathlib import Path
from typing import Any, Optional

# Default configuration values
DEFAULTS = {
    "last_download_path": str(Path.home() / "Downloads"),
    "default_video_format": "mp4",
    "default_audio_format": "mp3",
    "default_video_quality": "1080p",
    "default_audio_quality": "320kbps",
    "remember_location": True,
    "theme": "dark",
    "check_updates_on_start": True,
    # Spotify API credentials (for automatic track name extraction)
    "spotify_client_id": "",
    "spotify_client_secret": ""
}

class Config:
    """Configuration manager for the application."""
    
    def __init__(self):
        # Config file in user's app data
        self.config_dir = Path.home() / ".universal_downloader"
        self.config_file = self.config_dir / "config.json"
        self._config = {}
        self._load()
    
    def _load(self) -> None:
        """Load configuration from JSON file."""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
            except (json.JSONDecodeError, IOError):
                self._config = DEFAULTS.copy()
        else:
            self._config = DEFAULTS.copy()
    
    def _save(self) -> None:
        """Save configuration to JSON file."""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(self._config, f, indent=2, ensure_ascii=False)
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self._config.get(key, DEFAULTS.get(key, default))
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value and save."""
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
    
    def get_spotify_credentials(self) -> tuple:
        """Get Spotify API credentials."""
        return (
            self.get("spotify_client_id", ""),
            self.get("spotify_client_secret", "")
        )
    
    def set_spotify_credentials(self, client_id: str, client_secret: str) -> None:
        """Set Spotify API credentials."""
        self._config["spotify_client_id"] = client_id
        self._config["spotify_client_secret"] = client_secret
        self._save()
    
    def has_spotify_credentials(self) -> bool:
        """Check if Spotify credentials are configured."""
        client_id, client_secret = self.get_spotify_credentials()
        return bool(client_id and client_secret)
    
    def reset(self) -> None:
        """Reset to default configuration."""
        self._config = DEFAULTS.copy()
        self._save()


# Singleton instance
config = Config()
