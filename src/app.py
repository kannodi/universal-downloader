"""
Universal Downloader - Main Application
Modern GUI application using CustomTkinter for downloading media from YouTube, Spotify, and 1000+ sites.
"""

import customtkinter as ctk
from tkinter import messagebox
import os
from typing import Optional

try:
    import pygame
    PYGAME_LOADED = True
except ImportError:
    PYGAME_LOADED = False

from src.config import config
from src.dependency_checker import check_all_dependencies, update_yt_dlp, install_ffmpeg

# Component imports
from src.gui.colors import COLORS, SITE_COLORS
from src.gui.components.url_frame import UrlFrame
from src.gui.components.format_frame import FormatFrame
from src.gui.components.player_frame import PlayerFrame
from src.gui.components.search_results import SearchResults
from src.gui.controller import DownloadController


class DependencyDialog(ctk.CTkToplevel):
    """Dialog for checking and updating dependencies."""
    
    def __init__(self, parent, deps_status: dict):
        super().__init__(parent)
        self.title("Verificando Dependencias")
        self.geometry("450x350")
        self.configure(fg_color=COLORS["bg_dark"])
        self.resizable(False, False)
        
        # Center on parent
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets(deps_status)
    
    def _create_widgets(self, deps: dict):
        title = ctk.CTkLabel(
            self,
            text="Estado de Dependencias",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(pady=(20, 15))
        
        deps_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=10)
        deps_frame.pack(padx=20, pady=10, fill="x")
        
        self._dep_labels = {}
        for dep_name, dep_info in deps.items():
            if dep_name == "all_ok":
                continue
                
            row = ctk.CTkFrame(deps_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            
            icon = "[OK]" if dep_info["installed"] else "[XX]"
            color = COLORS["success"] if dep_info["installed"] else COLORS["error"]
            
            label = ctk.CTkLabel(
                row,
                text=f"{icon}  {dep_name.upper()}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=color
            )
            label.pack(side="left")
            
            msg = ctk.CTkLabel(
                row,
                text=dep_info["message"],
                font=ctk.CTkFont(size=12),
                text_color=COLORS["text_secondary"]
            )
            msg.pack(side="right")
            
            self._dep_labels[dep_name] = (label, msg)
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        # Show Install FFmpeg button if FFmpeg is missing, otherwise show Update yt-dlp
        if not deps.get("ffmpeg", {}).get("installed", False):
            self.action_btn = ctk.CTkButton(
                btn_frame,
                text="Instalar FFmpeg",
                command=self._install_ffmpeg_action,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                width=130
            )
        else:
            self.action_btn = ctk.CTkButton(
                btn_frame,
                text="Actualizar yt-dlp",
                command=self._update_ytdlp,
                fg_color=COLORS["accent"],
                hover_color=COLORS["accent_hover"],
                width=130
            )
        self.action_btn.pack(side="left", padx=5)

        self.restart_btn = ctk.CTkButton(
            btn_frame,
            text="Reiniciar",
            command=self._restart_app,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["accent"],
            width=100
        )
        self.restart_btn.pack(side="left", padx=5)
        
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(pady=5)
        
        continue_btn = ctk.CTkButton(
            self,
            text="Continuar",
            command=self.destroy,
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["accent"],
            width=200
        )
        continue_btn.pack(pady=15)

    def _update_ytdlp(self):
        self.status_label.configure(text="Actualizando yt-dlp...")
        self.action_btn.configure(state="disabled")
        self.update()
        
        def run_update():
            success, msg = update_yt_dlp()
            self.after(0, lambda: self.status_label.configure(
                text=msg,
                text_color=COLORS["success"] if success else COLORS["error"]
            ))
            self.after(0, lambda: self.action_btn.configure(state="normal"))
            
        import threading
        threading.Thread(target=run_update, daemon=True).start()

    def _install_ffmpeg_action(self):
        self.status_label.configure(text="Instalando FFmpeg globalmente...")
        self.action_btn.configure(state="disabled")
        self.update()
        
        def run_install():
            success, msg = install_ffmpeg()
            self.after(0, lambda: self.status_label.configure(
                text=msg,
                text_color=COLORS["success"] if success else COLORS["error"]
            ))
            self.after(0, lambda: self.action_btn.configure(state="normal"))
            
        import threading
        threading.Thread(target=run_install, daemon=True).start()

    def _restart_app(self):
        """Restarts the current python program."""
        import sys
        import subprocess
        # Get parent window to destroy it cleanly
        parent = self.master
        parent.destroy()
        
        # Spawn a new process of main.py
        subprocess.Popen([sys.executable, "main.py"])
        sys.exit()


class UniversalDownloader(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        self.title("Universal Downloader")
        self.geometry("520x580")
        self.configure(fg_color=COLORS["bg_dark"])
        self.minsize(480, 500)
        
        try:
            import tkinter as tk
            transparent_pixel = tk.PhotoImage(width=1, height=1)
            self.iconphoto(False, transparent_pixel)
        except:
            pass
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Instantiate controller
        self.controller = DownloadController(self)
        
        if PYGAME_LOADED:
            try:
                pygame.mixer.init()
            except:
                pass
        
        self._create_widgets()
        
        self.after(500, self._check_dependencies)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _check_dependencies(self):
        deps = check_all_dependencies()
        if not deps["all_ok"]:
            DependencyDialog(self, deps)
        else:
            self._update_status("Todas las dependencias están instaladas", "success")

    def _on_closing(self):
        self.controller.stop_preview()
        if PYGAME_LOADED:
            try:
                pygame.mixer.quit()
            except:
                pass
        try:
            cache_dir = os.path.join(os.getcwd(), ".audio_cache")
            if os.path.exists(cache_dir):
                import shutil
                shutil.rmtree(cache_dir, ignore_errors=True)
        except:
            pass
        self.destroy()

    def _create_widgets(self):
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=12, pady=(12, 8))
        
        # URL Component
        self.url_frame = UrlFrame(
            main_frame,
            on_analyze=self.controller.analyze_url,
            on_download=self.controller.start_download,
            on_paste=self.controller.analyze_url
        )
        self.url_frame.pack(fill="x", pady=(0, 0))
        
        # Playlist panel (hidden by default)
        self.playlist_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        playlist_inner = ctk.CTkFrame(self.playlist_frame, fg_color="transparent")
        playlist_inner.pack(fill="x", padx=10, pady=8)
        
        self.playlist_info_label = ctk.CTkLabel(
            playlist_inner, text="", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLORS["accent"]
        )
        self.playlist_info_label.pack(anchor="w")
        
        self.playlist_choice = ctk.StringVar(value="single")
        playlist_choice_frame = ctk.CTkFrame(playlist_inner, fg_color="transparent")
        playlist_choice_frame.pack(fill="x", pady=(4, 0))
        
        self.single_radio = ctk.CTkRadioButton(
            playlist_choice_frame, text="Solo este video",
            variable=self.playlist_choice, value="single",
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"]
        )
        self.single_radio.pack(side="left", padx=(0, 15))
        
        self.playlist_radio = ctk.CTkRadioButton(
            playlist_choice_frame, text="Playlist completa",
            variable=self.playlist_choice, value="playlist",
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"]
        )
        self.playlist_radio.pack(side="left")

        # Search results (hidden by default)
        self.results_frame = SearchResults(
            main_frame,
            on_preview_result=self.controller.preview_result,
            on_download_specific=self.controller.download_specific
        )

        # Info Frame
        self.info_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        info_inner = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        info_inner.pack(fill="x", padx=10, pady=8)
        
        # Horizontal layout for image and text
        self.info_layout = ctk.CTkFrame(info_inner, fg_color="transparent")
        self.info_layout.pack(fill="x", anchor="w")
        
        self.thumbnail_label = ctk.CTkLabel(
            self.info_layout, text="", width=110, height=62, fg_color=COLORS["bg_tertiary"], corner_radius=4
        )
        self.thumbnail_label.pack(side="left", padx=(0, 10))
        
        text_column = ctk.CTkFrame(self.info_layout, fg_color="transparent")
        text_column.pack(side="left", fill="both", expand=True)
        
        self.content_title_label = ctk.CTkLabel(
            text_column, text="", font=ctk.CTkFont(size=12), text_color=COLORS["text_secondary"],
            wraplength=310, justify="left", anchor="w"
        )
        self.content_title_label.pack(fill="x", anchor="w")
        
        self.open_link_btn = ctk.CTkButton(
            text_column, text="🔗 Abrir en Navegador", height=24, width=120,
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["accent"],
            command=self.controller.open_in_browser
        )
        self.open_link_btn.pack(anchor="w", pady=(6, 0))
        
        self.spotify_search_frame = ctk.CTkFrame(info_inner, fg_color="transparent")
        ctk.CTkLabel(
            self.spotify_search_frame, text="🔍 Nombre de canción y artista:",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(5, 2))
        
        self.spotify_search_entry = ctk.CTkEntry(
            self.spotify_search_frame, placeholder_text="Ej: Bad Bunny - Monaco",
            height=30, font=ctk.CTkFont(size=11), fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["spotify_green"], border_width=1
        )
        self.spotify_search_entry.pack(fill="x")

        # Player Component (hidden by default)
        self.player_frame = PlayerFrame(
            main_frame,
            on_toggle_playback=self.controller.toggle_playback,
            on_seek=self.controller.seek_audio
        )

        # Format component
        self.format_frame = FormatFrame(main_frame, on_type_change=self._on_type_change)
        self.format_frame.pack(fill="x", pady=(0, 4))

        # Formats Display
        self.formats_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        self.formats_frame.pack(fill="x", pady=(0, 4))
        formats_inner = ctk.CTkFrame(self.formats_frame, fg_color="transparent")
        formats_inner.pack(fill="x", padx=10, pady=6)
        
        self.available_formats_label = ctk.CTkLabel(
            formats_inner, text="Video: 1080p, 720p, 480p | Audio: 320kbps, 256kbps, 192kbps",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]
        )
        self.available_formats_label.pack(anchor="w")

        # Progress component
        progress_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        progress_frame.pack(fill="x", pady=(0, 4))
        progress_inner = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_inner.pack(fill="x", padx=10, pady=8)
        
        self.progress_label = ctk.CTkLabel(
            progress_inner, text="Listo para descargar", font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]
        )
        self.progress_label.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_inner, height=8, corner_radius=4, fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent"]
        )
        self.progress_bar.pack(fill="x", pady=(6, 0))
        self.progress_bar.set(0)

        # Status
        self.status_label = ctk.CTkLabel(
            main_frame, text="", font=ctk.CTkFont(size=10), text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(anchor="w", pady=(4, 0))

    def _show_playlist_options(self, playlist_info: dict):
        count = playlist_info.get('count', 0)
        title = playlist_info.get('title', 'Playlist')
        self.playlist_info_label.configure(text=f"{title} ({count} videos)")
        self.content_title_label.configure(
            text="Selecciona si deseas descargar solo el video actual o la playlist completa:",
            text_color=COLORS["text_primary"], wraplength=310
        )
        self.playlist_frame.pack(fill="x", pady=(0, 15), after=self.url_frame)
        self.playlist_choice.set("single")
        # Clear thumbnail for playlist info
        self.thumbnail_label.configure(image=None, text="")

    def _update_video_ui_simple(self, title: str, info: str, duration: int = 0, show_player: bool = True, thumbnail_url: str = None):
        d = int(duration) if duration else 0
        duration_str = f" • {d // 60}:{d % 60:02d}" if d else ""
        if self.format_frame.download_type.get() == "video":
            self.info_frame.pack(fill="x", pady=(10, 0), after=self.url_frame)
            self.player_frame.pack_forget()
            self.content_title_label.configure(text=f"{title}\n{info}{duration_str}", text_color=COLORS["text_primary"])
            
            # Download and set thumbnail
            if thumbnail_url:
                self._load_thumbnail_async(thumbnail_url)
            else:
                self.thumbnail_label.configure(image=None, text="")
        else:
            self.info_frame.pack_forget()
            self.player_frame.set_audio_title(f"{title} - {info}")
            if show_player:
                self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_frame)
            else:
                self.player_frame.pack_forget()
        
        self.available_formats_label.configure(
            text="Video: 1080p, 720p, 480p, 360p\nAudio: 320kbps, 256kbps, 192kbps, 128kbps"
        )

    def _load_thumbnail_async(self, url: str):
        """Downloads the video thumbnail and displays it on the UI as CTkImage."""
        def load():
            try:
                import requests
                from PIL import Image, ImageTk
                import io
                
                response = requests.get(url, timeout=5)
                if response.ok:
                    image_data = response.content
                    image = Image.open(io.BytesIO(image_data))
                    # Scale to 110x62 (16:9 ratio approximately)
                    image = image.resize((110, 62), Image.Resampling.LANCZOS)
                    
                    # Create CTkImage
                    ctk_image = ctk.CTkImage(light_image=image, dark_image=image, size=(110, 62))
                    
                    self.after(0, lambda: self.thumbnail_label.configure(image=ctk_image, text=""))
            except Exception as e:
                # Silently fail, just clear label text
                self.after(0, lambda: self.thumbnail_label.configure(image=None, text=""))
                
        import threading
        threading.Thread(target=load, daemon=True).start()

    def _update_spotify_ui(self, formats: dict, track_name: str = None):
        self.format_frame.download_type.set("audio")
        self._on_type_change()
        if track_name:
            self.player_frame.set_audio_title(f"Spotify: {track_name}")
            self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_frame)
            self.spotify_search_entry.delete(0, "end")
            self.spotify_search_entry.insert(0, track_name)
        else:
            self.player_frame.set_audio_title("Spotify detectado - Ingresa nombre para buscar")
            self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_frame)
        self.info_frame.pack(fill="x", pady=(10, 0), after=self.url_frame)
        self.spotify_search_frame.pack(fill="x", pady=(5, 0))
        self.available_formats_label.configure(
            text="Formatos: MP3, M4A, FLAC, WAV, OGG, OPUS\nSe buscara en YouTube y descargara con yt-dlp"
        )
        self.thumbnail_label.configure(image=None, text="")

    def _on_type_change(self):
        self.controller.stop_preview()
        is_video = self.format_frame.download_type.get() == "video"
        if is_video:
            self.player_frame.pack_forget()
            if self.content_title_label.cget("text"):
                self.info_frame.pack(fill="x", pady=(10, 0), after=self.url_frame)
        else:
            self.info_frame.pack_forget()
            if self.controller._preview_file and PYGAME_LOADED:
                self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_frame)

    def _update_status(self, message: str, status_type: str = "info"):
        colors = {
            "info": COLORS["text_secondary"], "success": COLORS["success"],
            "error": COLORS["error"], "warning": COLORS["warning"]
        }
        self.status_label.configure(text=message, text_color=colors.get(status_type, COLORS["text_secondary"]))

    def _update_site_theme(self, site_type: str):
        color = SITE_COLORS.get(site_type, SITE_COLORS["other"])
        self.url_frame.update_theme_color(color)
        self.format_frame.update_theme_color(color)
        self.player_frame.update_theme_color(color)
        self.open_link_btn.configure(hover_color=color)
        self.progress_bar.configure(progress_color=color)


def main():
    app = UniversalDownloader()
    app.mainloop()


if __name__ == "__main__":
    main()
