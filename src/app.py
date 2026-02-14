"""
Universal Downloader - Main Application
Modern GUI application using CustomTkinter for downloading media from YouTube, Spotify, and 1000+ sites.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
from typing import Optional

from src.config import config
from src.video_downloader import VideoDownloader, detect_url_type
from src.spotify_downloader import SpotifyDownloader, is_spotify_url
from src.dependency_checker import check_all_dependencies, update_yt_dlp, update_spotdl


# Theme colors
COLORS = {
    "bg_dark": "#0a0a0c",
    "bg_secondary": "#16161a",
    "bg_tertiary": "#23232e",
    "accent": "#7c3aed",
    "accent_hover": "#8b5cf6",
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "success": "#10b981",
    "error": "#f43f5e",
    "warning": "#f59e0b",
    "spotify_green": "#1db954",
    "youtube_red": "#ef4444"
}


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
        # Title
        title = ctk.CTkLabel(
            self,
            text="🔍 Estado de Dependencias",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title.pack(pady=(20, 15))
        
        # Dependencies frame
        deps_frame = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=10)
        deps_frame.pack(padx=20, pady=10, fill="x")
        
        self._dep_labels = {}
        
        for dep_name, dep_info in deps.items():
            if dep_name == "all_ok":
                continue
                
            row = ctk.CTkFrame(deps_frame, fg_color="transparent")
            row.pack(fill="x", padx=15, pady=8)
            
            # Status icon
            icon = "✅" if dep_info["installed"] else "❌"
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
        
        # Update buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        self.update_ytdlp_btn = ctk.CTkButton(
            btn_frame,
            text="⬆ Actualizar yt-dlp",
            command=self._update_ytdlp,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            width=150
        )
        self.update_ytdlp_btn.pack(side="left", padx=5)
        
        self.update_spotdl_btn = ctk.CTkButton(
            btn_frame,
            text="⬆ Actualizar spotDL",
            command=self._update_spotdl,
            fg_color=COLORS["spotify_green"],
            hover_color="#1ed760",
            width=150
        )
        self.update_spotdl_btn.pack(side="left", padx=5)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(pady=5)
        
        # Continue button
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
        self.update()
        success, msg = update_yt_dlp()
        self.status_label.configure(
            text=msg,
            text_color=COLORS["success"] if success else COLORS["error"]
        )
    
    def _update_spotdl(self):
        self.status_label.configure(text="Actualizando spotDL...")
        self.update()
        success, msg = update_spotdl()
        self.status_label.configure(
            text=msg,
            text_color=COLORS["success"] if success else COLORS["error"]
        )


class UniversalDownloader(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("🎵 Universal Downloader")
        self.geometry("700x750")
        self.configure(fg_color=COLORS["bg_dark"])
        self.minsize(650, 700)
        
        # Set theme
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Downloaders
        self.video_downloader = VideoDownloader(progress_callback=self._on_progress)
        self.spotify_downloader = SpotifyDownloader(progress_callback=self._on_progress)
        
        # State
        self._current_formats = None
        self._is_downloading = False
        self._playlist_info = None  # Stores playlist detection info
        self._download_url = None   # URL to actually download
        self._last_analyzed_url = None # Avoid redundant analysis
        
        # Create UI
        self._create_widgets()
        
        # Check dependencies on start
        self.after(500, self._check_dependencies)
    
    def _check_dependencies(self):
        """Check dependencies on startup."""
        deps = check_all_dependencies()
        if not deps["all_ok"]:
            DependencyDialog(self, deps)
        else:
            # Show quick status
            self._update_status("✅ Todas las dependencias están instaladas", "success")
    
    def _create_widgets(self):
        """Create all UI widgets."""
        
        # Main container with reduced padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # ===== HEADER (compact) =====
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 8))
        
        title_label = ctk.CTkLabel(
            header_frame,
            text="🎵 Universal Downloader",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=COLORS["text_primary"]
        )
        title_label.pack(side="left")
        
        subtitle_label = ctk.CTkLabel(
            header_frame,
            text="YouTube • Spotify • +1000 sitios",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        subtitle_label.pack(side="left", padx=(10, 0), pady=(4, 0))
        
        
        # ===== URL INPUT (compact) =====
        url_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        url_frame.pack(fill="x", pady=(0, 6))
        
        url_inner = ctk.CTkFrame(url_frame, fg_color="transparent")
        url_inner.pack(fill="x", padx=10, pady=8)
        
        url_row = ctk.CTkFrame(url_inner, fg_color="transparent")
        url_row.pack(fill="x")
        
        self.url_entry = ctk.CTkEntry(
            url_row,
            placeholder_text="Pega URL de YouTube, Spotify u otro sitio...",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["accent"],
            border_width=1
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        # Auto-analyze on paste
        self.url_entry.bind("<Control-v>", lambda e: self.after(100, self._analyze_url))
        self.url_entry.bind("<<Paste>>", lambda e: self.after(100, self._analyze_url))
        # Also on Return key
        self.url_entry.bind("<Return>", lambda e: self._analyze_url())
        
        self.analyze_btn = ctk.CTkButton(
            url_row,
            text="🔍 Analizar",
            command=self._analyze_url,
            width=90,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        )
        self.analyze_btn.pack(side="right")
        
        self.url_type_label = ctk.CTkLabel(
            url_inner,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_secondary"]
        )
        self.url_type_label.pack(anchor="w", pady=(2, 0))
        
        # ===== PLAYLIST OPTIONS (hidden by default) =====
        self.playlist_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        
        playlist_inner = ctk.CTkFrame(self.playlist_frame, fg_color="transparent")
        playlist_inner.pack(fill="x", padx=10, pady=8)
        
        self.playlist_info_label = ctk.CTkLabel(
            playlist_inner,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["accent"]
        )
        self.playlist_info_label.pack(anchor="w")
        
        self.playlist_choice = ctk.StringVar(value="single")
        playlist_choice_frame = ctk.CTkFrame(playlist_inner, fg_color="transparent")
        playlist_choice_frame.pack(fill="x", pady=(4, 0))
        
        self.single_radio = ctk.CTkRadioButton(
            playlist_choice_frame, text="🎬 Solo este video",
            variable=self.playlist_choice, value="single",
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"]
        )
        self.single_radio.pack(side="left", padx=(0, 15))
        
        self.playlist_radio = ctk.CTkRadioButton(
            playlist_choice_frame, text="📁 Playlist completa",
            variable=self.playlist_choice, value="playlist",
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"]
        )
        self.playlist_radio.pack(side="left")
        
        # ===== CONTENT INFO (compact) =====
        self.info_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        self.info_frame.pack(fill="x", pady=(0, 6))
        
        info_inner = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        info_inner.pack(fill="x", padx=10, pady=8)
        
        self.content_title_label = ctk.CTkLabel(
            info_inner,
            text="📋 Ingresa una URL y haz clic en Analizar",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            wraplength=550
        )
        self.content_title_label.pack(anchor="w")
        
        # Spotify search query input (hidden by default)
        self.spotify_search_frame = ctk.CTkFrame(info_inner, fg_color="transparent")
        # Don't pack yet - will show when Spotify detected
        
        ctk.CTkLabel(
            self.spotify_search_frame,
            text="🔍 Nombre de canción y artista:",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(5, 2))
        
        self.spotify_search_entry = ctk.CTkEntry(
            self.spotify_search_frame,
            placeholder_text="Ej: Bad Bunny - Monaco",
            height=30,
            font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["spotify_green"],
            border_width=1
        )
        self.spotify_search_entry.pack(fill="x")
        
        # ===== FORMAT SELECTION (compact - all in one row) =====
        format_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        format_frame.pack(fill="x", pady=(0, 6))
        
        format_inner = ctk.CTkFrame(format_frame, fg_color="transparent")
        format_inner.pack(fill="x", padx=10, pady=8)
        
        self.download_type = ctk.StringVar(value="video")
        
        self.video_radio = ctk.CTkRadioButton(
            format_inner, text="📹 Video",
            variable=self.download_type, value="video",
            command=self._on_type_change,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"]
        )
        self.video_radio.pack(side="left", padx=(0, 10))
        
        self.audio_radio = ctk.CTkRadioButton(
            format_inner, text="🎵 Audio",
            variable=self.download_type, value="audio",
            command=self._on_type_change,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"]
        )
        self.audio_radio.pack(side="left", padx=(0, 20))
        
        ctk.CTkLabel(format_inner, text="Calidad:", font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_primary"]).pack(side="left", padx=(0, 5))
        
        self.quality_combo = ctk.CTkComboBox(
            format_inner, values=["1080p", "720p", "480p", "360p"],
            width=100, height=28, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"],
            button_color=COLORS["accent"], dropdown_fg_color=COLORS["bg_tertiary"]
        )
        self.quality_combo.pack(side="left", padx=(0, 15))
        self.quality_combo.set("1080p")
        
        ctk.CTkLabel(format_inner, text="Formato:", font=ctk.CTkFont(size=11),
                     text_color=COLORS["text_primary"]).pack(side="left", padx=(0, 5))
        
        self.format_combo = ctk.CTkComboBox(
            format_inner, values=["mp4", "mkv", "webm"],
            width=80, height=28, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"],
            button_color=COLORS["accent"], dropdown_fg_color=COLORS["bg_tertiary"]
        )
        self.format_combo.pack(side="left")
        self.format_combo.set("mp4")
        
        # Discord compatibility row
        discord_row = ctk.CTkFrame(format_frame, fg_color="transparent")
        discord_row.pack(fill="x", padx=10, pady=(0, 8))
        
        self.discord_compat_var = ctk.BooleanVar(value=False)
        self.discord_compat_check = ctk.CTkCheckBox(
            discord_row, text="🎮 Discord Compatible (re-codifica a H.264)",
            variable=self.discord_compat_var,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.discord_compat_check.pack(side="left")
        
        discord_info = ctk.CTkLabel(
            discord_row, text="(TikTok se re-codifica automáticamente)",
            font=ctk.CTkFont(size=10),
            text_color=COLORS["text_secondary"]
        )
        discord_info.pack(side="left", padx=(10, 0))
        
        # ===== FORMATS DISPLAY (compact) =====
        self.formats_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        self.formats_frame.pack(fill="x", pady=(0, 6))
        
        formats_inner = ctk.CTkFrame(self.formats_frame, fg_color="transparent")
        formats_inner.pack(fill="x", padx=10, pady=6)
        
        self.available_formats_label = ctk.CTkLabel(
            formats_inner,
            text="📊 Video: 1080p, 720p, 480p | Audio: 320kbps, 256kbps, 192kbps",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.available_formats_label.pack(anchor="w")
        
        # ===== OUTPUT PATH (compact) =====
        path_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        path_frame.pack(fill="x", pady=(0, 6))
        
        path_inner = ctk.CTkFrame(path_frame, fg_color="transparent")
        path_inner.pack(fill="x", padx=10, pady=8)
        
        path_row = ctk.CTkFrame(path_inner, fg_color="transparent")
        path_row.pack(fill="x")
        
        ctk.CTkLabel(path_row, text="📁", font=ctk.CTkFont(size=12)).pack(side="left", padx=(0, 5))
        
        self.path_entry = ctk.CTkEntry(
            path_row, height=30, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"], border_width=1
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.insert(0, config.get_download_path())
        
        browse_btn = ctk.CTkButton(
            path_row, text="Examinar", command=self._browse_folder,
            width=70, height=30, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["accent"]
        )
        browse_btn.pack(side="right")
        
        self.remember_var = ctk.BooleanVar(value=config.get("remember_location", True))
        remember_check = ctk.CTkCheckBox(
            path_inner, text="Recordar ubicación",
            variable=self.remember_var, command=self._on_remember_change,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        remember_check.pack(anchor="w", pady=(6, 0))
        
        # ===== PROGRESS (compact) =====
        progress_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        progress_frame.pack(fill="x", pady=(0, 6))
        
        progress_inner = ctk.CTkFrame(progress_frame, fg_color="transparent")
        progress_inner.pack(fill="x", padx=10, pady=8)
        
        self.progress_label = ctk.CTkLabel(
            progress_inner, text="Listo para descargar",
            font=ctk.CTkFont(size=11), text_color=COLORS["text_secondary"]
        )
        self.progress_label.pack(anchor="w")
        
        self.progress_bar = ctk.CTkProgressBar(
            progress_inner, height=8, corner_radius=4,
            fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent"]
        )
        self.progress_bar.pack(fill="x", pady=(6, 0))
        self.progress_bar.set(0)
        
        # ===== DOWNLOAD BUTTON =====
        self.download_btn = ctk.CTkButton(
            main_frame, text="⬇️ Descargar", command=self._start_download,
            height=40, font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"], corner_radius=8
        )
        self.download_btn.pack(fill="x", pady=(2, 0))
        
        # ===== STATUS =====
        self.status_label = ctk.CTkLabel(
            main_frame, text="", font=ctk.CTkFont(size=10),
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(anchor="w", pady=(4, 0))
    
    def _browse_folder(self):
        """Open folder browser dialog."""
        folder = filedialog.askdirectory(
            initialdir=self.path_entry.get() or config.get_download_path()
        )
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            if self.remember_var.get():
                config.set_download_path(folder)
    
    def _on_remember_change(self):
        """Handle remember location checkbox change."""
        config.set("remember_location", self.remember_var.get())
        if self.remember_var.get():
            config.set_download_path(self.path_entry.get())
    
    def _on_type_change(self):
        """Handle download type radio button change."""
        if self.download_type.get() == "video":
            self.quality_combo.configure(values=["1080p", "720p", "480p", "360p"])
            self.quality_combo.set("1080p")
            self.format_combo.configure(values=["mp4", "mkv", "webm"])
            self.format_combo.set("mp4")
        else:
            self.quality_combo.configure(values=["320kbps", "256kbps", "192kbps", "128kbps"])
            self.quality_combo.set("320kbps")
            self.format_combo.configure(values=["mp3", "m4a", "wav", "flac", "ogg"])
            self.format_combo.set("mp3")
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update the status label."""
        colors = {
            "info": COLORS["text_secondary"],
            "success": COLORS["success"],
            "error": COLORS["error"],
            "warning": COLORS["warning"]
        }
        self.status_label.configure(text=message, text_color=colors.get(status_type, COLORS["text_secondary"]))
    
    def _analyze_url(self):
        """Analyze the URL and get available formats."""
        url = self.url_entry.get().strip()
        if not url:
            self._update_status("⚠️ Por favor ingresa una URL", "warning")
            return
            
        if url == self._last_analyzed_url:
            return
            
        self._last_analyzed_url = url
        self.analyze_btn.configure(state="disabled", text="Analizando...")
        self._update_status("🔍 Analizando URL...", "info")
        
        # Hide playlist frame and spotify search initially
        self.after(0, lambda: self.playlist_frame.pack_forget())
        self.after(0, lambda: self.spotify_search_frame.pack_forget())
        self._playlist_info = None
        self._download_url = url
        
        def analyze():
            try:
                url_type = detect_url_type(url)
                
                if url_type == "invalid":
                    self.after(0, lambda: self._update_status("❌ URL no válida", "error"))
                    self.after(0, lambda: self.analyze_btn.configure(state="normal", text="🔍 Analizar"))
                    return
                
                if url_type == "spotify":
                    # Spotify URL
                    self.after(0, lambda: self.url_type_label.configure(
                        text="🎵 Spotify detectado",
                        text_color=COLORS["spotify_green"]
                    ))
                    
                    # Try to get track name
                    track_name = self.spotify_downloader.get_track_name(url)
                    formats = self.spotify_downloader.get_available_formats()
                    
                    self.after(0, lambda: self._update_spotify_ui(formats, track_name))
                else:
                    # YouTube or other site - use fast detection
                    icon = "▶️ YouTube" if url_type == "youtube" else "🌐 Sitio compatible"
                    color = COLORS["youtube_red"] if url_type == "youtube" else COLORS["accent"]
                    self.after(0, lambda: self.url_type_label.configure(text=icon, text_color=color))
                    
                    # Fast playlist detection
                    playlist_info = self.video_downloader.get_playlist_info(url)
                    
                    if playlist_info:
                        if playlist_info.get('is_playlist'):
                            # It's a playlist - show options
                            self._playlist_info = playlist_info
                            self.after(0, lambda: self._show_playlist_options(playlist_info))
                            
                            # Get single video URL if available
                            single_url = self.video_downloader.get_single_video_url(url)
                            if single_url:
                                self._download_url = single_url
                            
                            # We only show the playlist options frame, which will update labels
                        else:
                            # Single video - use info from fast detection
                            title = playlist_info.get('title', 'Video')
                            uploader = playlist_info.get('uploader', '')
                            duration = playlist_info.get('duration', 0)
                            self.after(0, lambda: self._update_video_ui_simple(title, uploader, duration))
                    else:
                        # Fallback - just show ready to download
                        self.after(0, lambda: self._update_video_ui_simple("Contenido detectado", "Listo para descargar"))
                
                self.after(0, lambda: self._update_status("✅ Análisis completado", "success"))
            except Exception as e:
                self.after(0, lambda: self._update_status(f"❌ Error: {str(e)}", "error"))
            finally:
                self.after(0, lambda: self.analyze_btn.configure(state="normal", text="🔍 Analizar"))
        
        threading.Thread(target=analyze, daemon=True).start()
    
    def _show_playlist_options(self, playlist_info: dict):
        """Show playlist selection options."""
        count = playlist_info.get('count', 0)
        title = playlist_info.get('title', 'Playlist')
        
        self.playlist_info_label.configure(
            text=f"📚 {title} ({count} videos)"
        )
        
        # Update content title to guide the user
        self.content_title_label.configure(
            text="Selecciona si deseas descargar solo el video actual o la playlist completa:",
            text_color=COLORS["text_primary"]
        )
        
        # Show the playlist frame after URL section
        self.playlist_frame.pack(fill="x", pady=(0, 15), after=self.url_entry.master.master)
        self.playlist_choice.set("single")  # Default to single video
    
    def _update_video_ui(self, formats: dict):
        """Update UI with video format information."""
        self._current_formats = formats
        
        # Update content title
        title = formats.get('title', 'Desconocido')
        uploader = formats.get('uploader', '')
        duration = formats.get('duration', 0)
        duration_str = f" • {duration // 60}:{duration % 60:02d}" if duration else ""
        
        self.content_title_label.configure(
            text=f"🎬 {title}\n👤 {uploader}{duration_str}",
            text_color=COLORS["text_primary"]
        )
        
        # Update available formats display
        video_formats = formats.get('video', [])
        audio_formats = formats.get('audio', [])
        
        video_str = ", ".join([f"{v['quality']}" for v in video_formats[:6]])
        audio_str = ", ".join([f"{a['quality']}" for a in audio_formats[:6]])
        
        self.available_formats_label.configure(
            text=f"📹 Video: {video_str or 'N/A'}\n🎵 Audio: {audio_str or 'N/A'}"
        )
        
        # Update quality dropdown with actual available qualities
        if video_formats:
            qualities = [v['quality'] for v in video_formats]
            self.quality_combo.configure(values=qualities)
            self.quality_combo.set(qualities[0] if qualities else "1080p")
    
    def _update_video_ui_simple(self, title: str, info: str, duration: int = 0):
        """Update UI with basic info (fast, no format extraction)."""
        duration_str = f" • {duration // 60}:{duration % 60:02d}" if duration else ""
        
        self.content_title_label.configure(
            text=f"🎬 {title}\n👤 {info}{duration_str}",
            text_color=COLORS["text_primary"]
        )
        
        # Reset url_type_label to avoid double info if needed
        # But here we keep it as it's the site indicator
        
        # Show default format options
        self.available_formats_label.configure(
            text="📹 Video: 1080p, 720p, 480p, 360p\n🎵 Audio: 320kbps, 256kbps, 192kbps, 128kbps"
        )
    
    def _update_spotify_ui(self, formats: dict, track_name: str = None):
        """Update UI for Spotify content."""
        self._current_formats = formats
        
        if track_name:
            self.content_title_label.configure(
                text=f"🎵 {track_name}",
                text_color=COLORS["text_primary"]
            )
            # Pre-fill search with track name
            self.spotify_search_entry.delete(0, "end")
            self.spotify_search_entry.insert(0, track_name)
        else:
            self.content_title_label.configure(
                text="🎵 Spotify detectado\nIngresa el nombre de la canción para buscar en YouTube",
                text_color=COLORS["text_primary"]
            )
        
        # Show Spotify search input
        self.spotify_search_frame.pack(fill="x", pady=(5, 0))
        
        # Switch to audio mode for Spotify
        self.download_type.set("audio")
        self._on_type_change()
        
        self.available_formats_label.configure(
            text="🎵 Formatos: MP3, M4A, FLAC, WAV, OGG, OPUS\n📊 Se buscará en YouTube y descargará con yt-dlp"
        )
    
    def _on_progress(self, progress: dict):
        """Handle progress updates from downloaders."""
        status = progress.get('status', '')
        
        if status == 'downloading':
            percent = progress.get('percent', 0)
            self.after(0, lambda: self.progress_bar.set(percent / 100))
            self.after(0, lambda: self.progress_label.configure(
                text=f"Descargando... {percent:.1f}%"
            ))
        elif status == 'finished':
            self.after(0, lambda: self.progress_bar.set(1))
            self.after(0, lambda: self.progress_label.configure(text="✅ Descarga completada"))
            self.after(0, lambda: self._update_status("✅ Descarga completada exitosamente", "success"))
            self.after(0, lambda: self._set_downloading(False))
        elif status == 'error':
            error = progress.get('error', 'Error desconocido')
            self.after(0, lambda: self._update_status(f"❌ Error: {error}", "error"))
            self.after(0, lambda: self._set_downloading(False))
        elif status == 'starting':
            self.after(0, lambda: self.progress_label.configure(
                text=progress.get('message', 'Iniciando...')
            ))
    
    def _set_downloading(self, is_downloading: bool):
        """Set the downloading state."""
        self._is_downloading = is_downloading
        if is_downloading:
            self.download_btn.configure(state="disabled", text="⏳ Descargando...")
            self.analyze_btn.configure(state="disabled")
        else:
            self.download_btn.configure(state="normal", text="⬇️ Descargar")
            self.analyze_btn.configure(state="normal")
    
    def _start_download(self):
        """Start the download process."""
        url = self.url_entry.get().strip()
        output_path = self.path_entry.get().strip()
        
        if not url:
            self._update_status("⚠️ Por favor ingresa una URL", "warning")
            return
        
        if not output_path or not os.path.isdir(output_path):
            self._update_status("⚠️ Por favor selecciona una carpeta válida", "warning")
            return
        
        # Save path if remember is enabled
        if self.remember_var.get():
            config.set_download_path(output_path)
        
        self._set_downloading(True)
        self.progress_bar.set(0)
        
        def download():
            try:
                url_type = detect_url_type(url)
                quality = self.quality_combo.get()
                format_type = self.format_combo.get()
                download_type = self.download_type.get()
                
                # Determine actual download URL based on playlist choice
                actual_url = url
                if self._playlist_info and self._playlist_info.get('is_playlist'):
                    if self.playlist_choice.get() == "single" and self._download_url:
                        actual_url = self._download_url
                    # else: use original URL for full playlist
                
                if url_type == "spotify":
                    # Spotify download - use search query
                    search_query = self.spotify_search_entry.get().strip()
                    if not search_query:
                        self.after(0, lambda: self._update_status("⚠️ Ingresa el nombre de la canción", "warning"))
                        self.after(0, lambda: self._set_downloading(False))
                        return
                    
                    success, msg = self.spotify_downloader.download(
                        url, output_path, format_type, quality, search_query
                    )
                    if not success:
                        self.after(0, lambda: self._update_status(f"❌ {msg}", "error"))
                else:
                    # Video/Audio download
                    # Check if Discord compatibility is enabled
                    force_reencode = self.discord_compat_var.get()
                    
                    # Determine if we should download as playlist
                    download_as_playlist = False
                    if self._playlist_info and self._playlist_info.get('is_playlist'):
                        download_as_playlist = (self.playlist_choice.get() == "playlist")
                    
                    if download_type == "video":
                        success = self.video_downloader.download_video(
                            actual_url, output_path, quality, format_type, 
                            force_reencode, download_as_playlist
                        )
                    else:
                        success = self.video_downloader.download_audio(
                            actual_url, output_path, quality, format_type,
                            download_as_playlist
                        )
                    
                    if not success:
                        self.after(0, lambda: self._update_status("❌ Error en la descarga", "error"))
            except Exception as e:
                self.after(0, lambda: self._update_status(f"❌ Error: {str(e)}", "error"))
                self.after(0, lambda: self._set_downloading(False))
        
        threading.Thread(target=download, daemon=True).start()
    


def main():
    """Main entry point."""
    app = UniversalDownloader()
    app.mainloop()


if __name__ == "__main__":
    main()
