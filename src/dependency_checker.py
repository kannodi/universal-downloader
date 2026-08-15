"""
Universal Downloader - Dependency Checker
Checks for FFmpeg and other required tools on startup.
"""

import subprocess
import sys
import re
import os
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
    extracting it globally, and setting machine PATH using an elevated PowerShell script.
    """
    if sys.platform != 'win32':
        return False, "Solo disponible en Windows"
    
    import urllib.request
    import tempfile
    
    zip_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    
    try:
        # Create temp files
        temp_dir = tempfile.gettempdir()
        zip_path = os.path.join(temp_dir, "ffmpeg.zip")
        ps_script_path = os.path.join(temp_dir, "install_ffmpeg.ps1")
        
        # 1. Download ZIP file
        urllib.request.urlretrieve(zip_url, zip_path)
        
        # 2. Write elevated PowerShell installation script
        ps_script_content = f"""
$zipPath = "{zip_path}"
$destDir = "C:\\Program Files\\FFmpeg"
$binPath = "C:\\Program Files\\FFmpeg\\bin"

# Ensure clean destination directory
if (Test-Path $destDir) {{
    Remove-Item -Path $destDir -Recurse -Force
}}
New-Item -ItemType Directory -Force -Path $destDir

# Extract ZIP file
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $destDir)

# FFmpeg extracts to a subfolder like ffmpeg-6.1-essentials_build
$subfolder = Get-ChildItem -Path $destDir | Where-Object {{ $_.PSIsContainer }} | Select-Object -First 1

if ($subfolder) {{
    # Move binaries to bin root folder
    Move-Item -Path "$($subfolder.FullName)\\*" -Destination $destDir -Force
    Remove-Item -Path $subfolder.FullName -Recurse -Force
}}

# Add FFmpeg to Machine Path globally if not already present
$path = [Environment]::GetEnvironmentVariable("Path", "Machine")
if ($path -notlike "*$binPath*") {{
    [Environment]::SetEnvironmentVariable("Path", "$path;$binPath", "Machine")
}}
"""
        with open(ps_script_path, "w", encoding="utf-8") as f:
            f.write(ps_script_content)
            
        # 3. Launch PowerShell script elevated using UAC (RunAs verb)
        cmd = f"Start-Process powershell -ArgumentList '-NoProfile -ExecutionPolicy Bypass -File \"{ps_script_path}\"' -Verb RunAs -Wait"
        
        result = subprocess.run(
            ["powershell", "-Command", cmd],
            capture_output=True,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        
        # Clean up temp script files
        try:
            if os.path.exists(zip_path):
                os.remove(zip_path)
            if os.path.exists(ps_script_path):
                os.remove(ps_script_path)
        except:
            pass
            
        if result.returncode == 0:
            return True, "FFmpeg instalado de forma global. Reinicia la aplicación."
        else:
            return False, "Error al solicitar permisos o instalar."
            
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
