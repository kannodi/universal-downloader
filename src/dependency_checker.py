"""
Universal Downloader - Dependency Checker
Checks for FFmpeg and other required tools on startup.
"""

import subprocess
import sys
import re
import os
from typing import Tuple, Optional
from src.runtime import BIN_DIR, binary_path


def check_ffmpeg() -> Tuple[bool, Optional[str], str]:
    """
    Check if FFmpeg is installed and get its version.

    Returns:
        Tuple of (is_installed, version_string, message)
    """
    ffmpeg_cmd = binary_path('ffmpeg')

    try:
        result = subprocess.run(
            [ffmpeg_cmd, '-version'],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
        )
        if result.returncode == 0:
            output = result.stdout
            match = re.search(r'ffmpeg version (\S+)', output)
            ver = match.group(1) if match else "unknown"
            return True, ver, f"FFmpeg {ver} encontrado"
        else:
            return False, None, "No funciona correctamente"
    except FileNotFoundError:
        return False, None, "No instalado"
    except Exception as e:
        return False, None, f"Error: {str(e)}"


def install_ffmpeg() -> Tuple[bool, str]:
    """
    Install FFmpeg by downloading gyan.dev release essentials zip,
    and extracting the binaries to a local 'bin' directory.
    """
    import urllib.request
    import tempfile
    import zipfile

    zip_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    if sys.platform != 'win32':
        return False, "Instala FFmpeg con el gestor de paquetes de tu sistema."
    bin_dir = str(BIN_DIR)

    try:
        os.makedirs(bin_dir, exist_ok=True)

        # Unique temporary directory is cleaned up on success and failure.
        with tempfile.TemporaryDirectory(prefix="universal-downloader-ffmpeg-") as temp_dir:
            zip_path = os.path.join(temp_dir, "ffmpeg.zip")
            import shutil
            with urllib.request.urlopen(zip_url, timeout=60) as response:
                with open(zip_path, "wb") as output:
                    shutil.copyfileobj(response, output)
            with zipfile.ZipFile(zip_path, 'r') as archive:
                members = {os.path.basename(item.filename): item for item in archive.infolist()
                           if os.path.basename(item.filename) in {'ffmpeg.exe', 'ffprobe.exe'}}
                if set(members) != {'ffmpeg.exe', 'ffprobe.exe'}:
                    return False, "El archivo descargado no contiene FFmpeg y FFprobe."
                for name, member in members.items():
                    with archive.open(member) as source, open(os.path.join(bin_dir, name), 'wb') as output:
                        shutil.copyfileobj(source, output)

        return True, "FFmpeg instalado localmente. Reinicia la aplicación."

    except Exception as e:
        return False, f"Error: {str(e)}"



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
