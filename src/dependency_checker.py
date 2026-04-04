"""
Universal Downloader - Dependency Checker
Checks for FFmpeg and other required tools on startup.
"""

import subprocess
import sys
import re
from typing import Tuple, Optional
from packaging import version


def check_ffmpeg() -> Tuple[bool, Optional[str], str]:
    """
    Check if FFmpeg is installed and get its version.
    
    Returns:
        Tuple of (is_installed, version_string, message)
    """
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        if result.returncode == 0:
            # Extract version from output
            output = result.stdout
            match = re.search(r'ffmpeg version (\S+)', output)
            ver = match.group(1) if match else "unknown"
            return True, ver, f"FFmpeg {ver} encontrado"
        else:
            return False, None, "FFmpeg no está funcionando correctamente"
    except FileNotFoundError:
        return False, None, "FFmpeg no está instalado. Por favor instálalo desde ffmpeg.org"
    except Exception as e:
        return False, None, f"Error al verificar FFmpeg: {str(e)}"


def check_yt_dlp() -> Tuple[bool, Optional[str], str]:
    """
    Check if yt-dlp is installed and check for updates.
    
    Returns:
        Tuple of (is_installed, version_string, message)
    """
    try:
        import yt_dlp
        current_version = yt_dlp.version.__version__
        return True, current_version, f"yt-dlp {current_version} encontrado"
    except ImportError:
        return False, None, "yt-dlp no está instalado"
    except Exception as e:
        return False, None, f"Error al verificar yt-dlp: {str(e)}"


def check_all_dependencies() -> dict:
    """
    Check all required dependencies.
    
    Returns:
        Dictionary with status of each dependency
    """
    ffmpeg_ok, ffmpeg_ver, ffmpeg_msg = check_ffmpeg()
    ytdlp_ok, ytdlp_ver, ytdlp_msg = check_yt_dlp()
    
    return {
        "ffmpeg": {
            "installed": ffmpeg_ok,
            "version": ffmpeg_ver,
            "message": ffmpeg_msg
        },
        "yt_dlp": {
            "installed": ytdlp_ok,
            "version": ytdlp_ver,
            "message": ytdlp_msg
        },
        "all_ok": ffmpeg_ok and ytdlp_ok
    }


def update_yt_dlp() -> Tuple[bool, str]:
    """
    Update yt-dlp to the latest version.
    
    Returns:
        Tuple of (success, message)
    """
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--upgrade', 'yt-dlp'],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            return True, "yt-dlp actualizado correctamente"
        else:
            return False, f"Error al actualizar: {result.stderr}"
    except Exception as e:
        return False, f"Error al actualizar: {str(e)}"
