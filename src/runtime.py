"""Shared executable discovery and yt-dlp runtime options.

Paths are anchored to the source tree, independently of the launch directory.
"""

from pathlib import Path
import sys

from src.config import config

PROJECT_ROOT = Path(__file__).resolve().parent.parent
BIN_DIR = PROJECT_ROOT / "bin"


def binary_path(name: str, custom_location: str | None = None) -> str:
    executable = f"{name}.exe" if sys.platform == "win32" else name
    if custom_location:
        custom = Path(custom_location)
        candidate = custom / executable if custom.is_dir() else custom.with_name(executable)
        if candidate.is_file():
            return str(candidate)
    candidate = BIN_DIR / executable
    return str(candidate) if candidate.is_file() else name


def ydl_options(defaults: dict | None = None) -> dict:
    """Return fresh options shared by downloaders and previews."""
    options = {"quiet": True, "no_warnings": True, "socket_timeout": 10}
    options.update(defaults or {})
    browser = config.get("browser_cookies", "none")
    if browser != "none":
        options["cookiesfrombrowser"] = (browser,)
    executable = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    if (BIN_DIR / executable).is_file():
        options["ffmpeg_location"] = str(BIN_DIR)
    return options
