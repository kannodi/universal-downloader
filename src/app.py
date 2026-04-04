"""
Universal Downloader - Main Application
Modern GUI application using CustomTkinter for downloading media from YouTube, Spotify, and 1000+ sites.
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import threading
import os
import time
from typing import Optional
try:
    import pygame
    PYGAME_LOADED = True
except ImportError:
    PYGAME_LOADED = False

from src.config import config
from src.video_downloader import VideoDownloader, detect_url_type
from src.spotify_downloader import SpotifyDownloader, is_spotify_url
from src.dependency_checker import check_all_dependencies, update_yt_dlp


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
    "error": "#FF0000",
    "warning": "#f59e0b",
    "spotify_green": "#1db954",
    "twitter_blue": "#1da1f2",
    "tiktok_pink": "#ff0050",
    "facebook_blue": "#1877f2",
    "gray": "#4b5563",
    "youtube_red": "#FF0000"
}

# Site color mapping
SITE_COLORS = {
    "youtube": COLORS["error"],
    "spotify": COLORS["spotify_green"],
    "twitter": COLORS["twitter_blue"],
    "tiktok": COLORS["tiktok_pink"],
    "facebook": COLORS["facebook_blue"],
    "search": COLORS["accent"],
    "other": COLORS["accent"]
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
            text="Estado de Dependencias",
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
        
        # Update buttons frame
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=15)
        
        self.update_ytdlp_btn = ctk.CTkButton(
            btn_frame,
            text="Actualizar yt-dlp",
            command=self._update_ytdlp,
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            width=200
        )
        self.update_ytdlp_btn.pack(side="left", padx=5)
        
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


class UniversalDownloader(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Window setup
        self.title("Universal Downloader")
        self.geometry("520x580")
        self.configure(fg_color=COLORS["bg_dark"])
        self.minsize(480, 500)
        
        # Remove default icon (Tkinter icon)
        try:
            import tkinter as tk
            # Create a transparent pixel for the icon
            transparent_pixel = tk.PhotoImage(width=1, height=1)
            self.iconphoto(False, transparent_pixel)
        except:
            pass
        
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
        self._is_analyzing = False     # Guard for concurrent analysis
        self._preview_playing = False  # Audio player state
        self._preview_file = None      # Current preview file path
        self._active_player_widgets = None # Dictionary of {slider, time_label, play_btn}
        self._playback_start_offset = 0 # Track absolute position after seeking
        self._is_paused = False # Flag to track if playback is explicitly paused
        self._expanded_row = None # Track the currently expanded search result row
        
        # Initialize pygame mixer
        if PYGAME_LOADED:
            try:
                pygame.mixer.init()
            except:
                pass
        
        # Initialize Always on Top
        self.always_on_top_var = ctk.BooleanVar(value=config.get("always_on_top", False))
        self.attributes("-topmost", self.always_on_top_var.get())
        
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
            self._update_status("Todas las dependencias están instaladas", "success")
    
    def _create_widgets(self):
        """Create all UI widgets."""
        
        # Main container with reduced padding
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(fill="both", expand=True, padx=12, pady=(12, 8))
        
        # ===== URL INPUT (compact) =====
        # Sub-frames for different sections
        self.url_row_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        self.url_row_frame.pack(fill="x", pady=(0, 0))
        
        url_inner = ctk.CTkFrame(self.url_row_frame, fg_color="transparent")
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
        self.url_entry.bind("<Return>", self._on_url_enter)
        
        self.analyze_btn = ctk.CTkButton(
            url_row,
            text="Analizar",
            command=self._analyze_url,
            width=80,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        )
        self.analyze_btn.pack(side="right", padx=(5, 0))

        self.download_btn = ctk.CTkButton(
            url_row,
            text="Descargar",
            command=self._start_download,
            width=90,
            height=32,
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        )
        self.download_btn.pack(side="right", padx=(5, 0))
        
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
        
        # ===== SEARCH RESULTS (hidden by default) =====
        self.results_frame = ctk.CTkScrollableFrame(
            main_frame, fg_color=COLORS["bg_secondary"], 
            corner_radius=8, height=120
        )
        # Don't pack yet
        
        # ===== INFO SECTION (Analysis results) =====
        self.info_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        # Won't pack yet to avoid empty gray box
        
        info_inner = ctk.CTkFrame(self.info_frame, fg_color="transparent")
        info_inner.pack(fill="x", padx=10, pady=8)
        
        self.content_title_label = ctk.CTkLabel(
            info_inner,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=COLORS["text_secondary"],
            wraplength=420
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
        
        # ===== AUDIO PLAYER (compact, hidden by default) =====
        self.player_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        # Don't pack yet
        
        player_container = ctk.CTkFrame(self.player_frame, fg_color="transparent")
        player_container.pack(fill="x", padx=10, pady=8)

        self.audio_title_label = ctk.CTkLabel(
            player_container, text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
            wraplength=400
        )
        self.audio_title_label.pack(anchor="w", pady=(0, 5))
        
        player_row = ctk.CTkFrame(player_container, fg_color="transparent")
        player_row.pack(fill="x")
        
        self.play_btn = ctk.CTkButton(
            player_row, text="▶", width=30, height=30,
            command=self._toggle_playback,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]
        )
        self.play_btn.pack(side="left", padx=(0, 10))
        
        self.player_slider = ctk.CTkSlider(
            player_row, from_=0, to=100, height=16,
            command=self._seek_audio,
            fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent"]
        )
        self.player_slider.pack(side="left", fill="x", expand=True)
        self.player_slider.set(0)
        
        self.time_label = ctk.CTkLabel(
            self.player_frame, text="00:00 / 00:00",
            font=ctk.CTkFont(size=10), text_color=COLORS["text_secondary"]
        )
        self.time_label.pack(anchor="e")
        
        # ===== FORMAT SELECTION (compact) =====
        format_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        format_frame.pack(fill="x", pady=(0, 4))
        
        format_inner = ctk.CTkFrame(format_frame, fg_color="transparent")
        format_inner.pack(fill="x", padx=10, pady=8)
        
        self.download_type = ctk.StringVar(value="video")
        
        # Single Row: Video/Audio, Quality, and Format
        row1 = ctk.CTkFrame(format_inner, fg_color="transparent")
        row1.pack(fill="x")
        
        # Radios
        self.video_radio = ctk.CTkRadioButton(
            row1, text="Video", variable=self.download_type, value="video",
            command=self._on_type_change, width=70,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"], border_color=COLORS["accent"]
        )
        self.video_radio.pack(side="left", padx=(0, 8))
        
        self.audio_radio = ctk.CTkRadioButton(
            row1, text="Audio", variable=self.download_type, value="audio",
            command=self._on_type_change, width=70,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"], border_color=COLORS["accent"]
        )
        self.audio_radio.pack(side="left", padx=(0, 10))
        
        # Quality
        quality_label = ctk.CTkLabel(row1, text="Res:", font=ctk.CTkFont(size=11), text_color=COLORS["text_primary"])
        quality_label.pack(side="left", padx=(0, 2))
        
        self.quality_combo = ctk.CTkComboBox(
            row1, values=["Mejor", "1080p", "720p", "480p", "360p"],
            width=95, height=26, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"],
            button_color=COLORS["accent"], dropdown_fg_color=COLORS["bg_tertiary"]
        )
        self.quality_combo.pack(side="left", padx=(0, 10))
        self.quality_combo.set("1080p")
        
        # Format
        format_label = ctk.CTkLabel(row1, text="Fmt:", font=ctk.CTkFont(size=11), text_color=COLORS["text_primary"])
        format_label.pack(side="left", padx=(0, 2))
        
        self.format_combo = ctk.CTkComboBox(
            row1, values=["mp4", "mkv", "webm"],
            width=85, height=26, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"],
            button_color=COLORS["accent"], dropdown_fg_color=COLORS["bg_tertiary"]
        )
        self.format_combo.pack(side="left")
        self.format_combo.set("mp4")
        
        
        # ===== FORMATS DISPLAY (compact) =====
        self.formats_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        self.formats_frame.pack(fill="x", pady=(0, 4))
        
        formats_inner = ctk.CTkFrame(self.formats_frame, fg_color="transparent")
        formats_inner.pack(fill="x", padx=10, pady=6)
        
        self.available_formats_label = ctk.CTkLabel(
            formats_inner,
            text="Video: 1080p, 720p, 480p | Audio: 320kbps, 256kbps, 192kbps",
            font=ctk.CTkFont(size=11),
            text_color=COLORS["text_secondary"]
        )
        self.available_formats_label.pack(anchor="w")
        
        # ===== OUTPUT PATH (compact) =====
        path_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        path_frame.pack(fill="x", pady=(0, 4))
        
        path_inner = ctk.CTkFrame(path_frame, fg_color="transparent")
        path_inner.pack(fill="x", padx=10, pady=8)
        
        path_row = ctk.CTkFrame(path_inner, fg_color="transparent")
        path_row.pack(fill="x")
        
        ctk.CTkLabel(path_row, text="Ruta:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 5))
        
        self.path_entry = ctk.CTkEntry(
            path_row, height=30, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"], border_width=1
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.insert(0, config.get_download_path())
        
        self.browse_btn = ctk.CTkButton(
            path_row, text="Examinar", command=self._browse_folder,
            width=70, height=30, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["accent"]
        )
        self.browse_btn.pack(side="right")
        
        self.remember_var = ctk.BooleanVar(value=config.get("remember_location", True))
        self.remember_check = ctk.CTkCheckBox(
            path_inner, text="Recordar ubicación",
            variable=self.remember_var, command=self._on_remember_change,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.remember_check.pack(side="left", pady=(6, 0))
        
        self.always_on_top_check = ctk.CTkCheckBox(
            path_inner, text="Mantener siempre arriba",
            variable=self.always_on_top_var, command=self._toggle_always_on_top,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.always_on_top_check.pack(side="left", padx=(20, 0), pady=(6, 0))
        
        # ===== PROGRESS (compact) =====
        progress_frame = ctk.CTkFrame(main_frame, fg_color=COLORS["bg_secondary"], corner_radius=8)
        progress_frame.pack(fill="x", pady=(0, 4))
        
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
        
        # Download button moved to top row
        
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
            
    def _toggle_always_on_top(self):
        """Toggle always on top window state."""
        is_on_top = self.always_on_top_var.get()
        self.attributes("-topmost", is_on_top)
        config.set("always_on_top", is_on_top)
    
    def _on_type_change(self):
        """Handle download type radio button change."""
        self._stop_preview()
        is_video = self.download_type.get() == "video"
        
        # Update quality and format combos
        if is_video:
            self.quality_combo.configure(values=["1080p", "720p", "480p"])
            self.quality_combo.set("1080p")
            self.format_combo.configure(values=["mp4", "mkv"])
            self.format_combo.set("mp4")
            
            self.player_frame.pack_forget()
            if self.content_title_label.cget("text"):
                self._show_info_frame()
        else:
            self.quality_combo.configure(values=["320kbps", "256kbps", "192kbps"])
            self.quality_combo.set("320kbps")
            self.format_combo.configure(values=["mp3", "m4a", "wav", "flac"])
            self.format_combo.set("mp3")
            
            self.info_frame.pack_forget()
            if self._preview_file and PYGAME_LOADED:
                self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_row_frame)

    def _show_info_frame(self):
        """Helper to show info frame in the correct position."""
        self.info_frame.pack(fill="x", pady=(10, 0), after=self.url_row_frame)
    
    def _update_status(self, message: str, status_type: str = "info"):
        """Update the status label."""
        colors = {
            "info": COLORS["text_secondary"],
            "success": COLORS["success"],
            "error": COLORS["error"],
            "warning": COLORS["warning"]
        }
        self.status_label.configure(text=message, text_color=colors.get(status_type, COLORS["text_secondary"]))
    
    def _on_url_enter(self, event=None):
        """Handle Enter key in URL entry. First enter analyzes, second enter downloads."""
        url = self.url_entry.get().strip()
        if not url:
            self._update_status("⚠️ Por favor ingresa una URL", "warning")
            return
            
        # If it's already analyzed and not currently analyzing/downloading, start download
        if url == self._last_analyzed_url and not self._is_analyzing and not self._is_downloading:
            self._start_download()
        else:
            self._analyze_url()

    def _analyze_url(self):
        """Analyze the URL and get available formats."""
        url = self.url_entry.get().strip()
        if not url:
            self._update_status("Por favor ingresa una URL", "warning")
            return
            
        def _clear_analysis_ui():
            self.playlist_frame.pack_forget()
            self.spotify_search_frame.pack_forget()
            self.player_frame.pack_forget()
            self.results_frame.pack_forget()
            self.info_frame.pack_forget()
            self._stop_preview()

        _clear_analysis_ui()
        if url == self._last_analyzed_url or self._is_analyzing:
            return
            
        self._is_analyzing = True
        self._last_analyzed_url = url
        self.analyze_btn.configure(state="disabled", text="Analizando...")
        self._update_status("🔍 Analizando URL...", "info")
        
        self._active_player_widgets = None
        self._playlist_info = None
        self._download_url = url
        
        def analyze():
            try:
                url_type = detect_url_type(url)
                
                if url_type == "invalid":
                    self.after(0, lambda: self._update_status("URL no válida", "error"))
                    self.after(0, lambda: self.analyze_btn.configure(state="normal", text="Analizar"))
                    return
                if url_type == "spotify":
                    self.after(0, lambda: self._update_site_theme("spotify"))
                    
                    # Try to get track name
                    track_name = self.spotify_downloader.get_track_name(url)
                    formats = self.spotify_downloader.get_available_formats()
                    
                    self.after(0, lambda: self._update_spotify_ui(formats, track_name))
                elif url_type == "search":
                    # YouTube search query - GET 5 RESULTS
                    self.after(0, lambda: self._update_site_theme("search"))
                    self.after(0, lambda: self._update_status("🔍 Buscando mejores resultados...", "info"))
                    
                    results = self.video_downloader.search_videos(url, count=5)
                    self.after(0, lambda: self._show_search_results(results))
                else:
                    # YouTube or other site - use fast detection
                    self.after(0, lambda: self._update_site_theme(url_type))
                    
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
                
                self.after(0, lambda: self._update_status("Análisis completado", "success"))
                
                # If audio mode or search, show player frame (if we have duration and pygame)
                if PYGAME_LOADED and url_type in ["youtube", "spotify"] and self.download_type.get() == "audio":
                    self.after(0, lambda: self.player_frame.pack(fill="x", pady=(5, 0)))
                elif not PYGAME_LOADED and self.download_type.get() == "audio":
                    self.after(0, lambda: self._update_status("Análisis OK. Instala 'pygame' para pre-escucha.", "info"))
            except Exception as e:
                self.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
            finally:
                self._is_analyzing = False
                self.after(0, lambda: self.analyze_btn.configure(state="normal", text="Analizar"))
        
        threading.Thread(target=analyze, daemon=True).start()
    
    def _show_playlist_options(self, playlist_info: dict):
        """Show playlist selection options."""
        count = playlist_info.get('count', 0)
        title = playlist_info.get('title', 'Playlist')
        
        self.playlist_info_label.configure(
            text=f"{title} ({count} videos)"
        )
        
        # Update content title to guide the user
        self.content_title_label.configure(
            text="Selecciona si deseas descargar solo el video actual o la playlist completa:",
            text_color=COLORS["text_primary"],
            wraplength=420
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
            text=f"{title}\nCanal: {uploader}{duration_str}",
            text_color=COLORS["text_primary"],
            wraplength=420
        )
        
        # Update available formats display
        video_formats = formats.get('video', [])
        audio_formats = formats.get('audio', [])
        
        video_str = ", ".join([f"{v['quality']}" for v in video_formats[:6]])
        audio_str = ", ".join([f"{a['quality']}" for a in audio_formats[:6]])
        
        self.available_formats_label.configure(
            text=f"Video: {video_str or 'N/A'}\nAudio: {audio_str or 'N/A'}"
        )
        
        # Update quality dropdown with actual available qualities
        if video_formats:
            qualities = [v['quality'] for v in video_formats]
            self.quality_combo.configure(values=qualities)
            self.quality_combo.set(qualities[0] if qualities else "1080p")
    
    def _update_site_theme(self, site_type: str):
        """Update the UI colors based on the detected site."""
        color = SITE_COLORS.get(site_type, SITE_COLORS["other"])
        
        # Site name map
        site_names = {
            "youtube": "YouTube", "spotify": "Spotify", "twitter": "Twitter / X",
            "tiktok": "TikTok", "facebook": "Facebook", "search": "Busqueda", "other": "Sitio compatible"
        }
        
        # Update widgets that use the site color
        self.url_entry.configure(border_color=color)
        for btn in [self.analyze_btn, self.download_btn]:
            btn.configure(fg_color=color, hover_color=color)
        
        self.progress_bar.configure(progress_color=color)
        
        for radio in [self.video_radio, self.audio_radio]:
            radio.configure(fg_color=color, border_color=color)
        self.path_entry.configure(border_color=color)
        self.browse_btn.configure(hover_color=color)
        self.remember_check.configure(fg_color=color)
        self.always_on_top_check.configure(fg_color=color)
        
        # Update Player check and combos
        self.play_btn.configure(fg_color=color, hover_color=color)
        self.player_slider.configure(progress_color=color)
        
        self.quality_combo.configure(border_color=color, button_color=color)
        self.format_combo.configure(border_color=color, button_color=color)
        
        self.remember_var.set(config.get("remember_location", True)) # Ensure var sync
        
    def _update_video_ui_simple(self, title: str, info: str, duration: int = 0, show_player: bool = True):
        """Update UI with basic info (fast, no format extraction)."""
        d = int(duration) if duration else 0
        duration_str = f" • {d // 60}:{d % 60:02d}" if d else ""
        
        if self.download_type.get() == "video":
            self.info_frame.pack(fill="x", pady=(10, 0), after=self.url_row_frame)
            self.player_frame.pack_forget()
            self.content_title_label.configure(
                text=f"{title}\n{info}{duration_str}",
                text_color=COLORS["text_primary"]
            )
        else:
            self.info_frame.pack_forget()
            self.audio_title_label.configure(text=f"{title} - {info}")
            # Show player row immediately in audio mode ONLY if requested
            if show_player:
                self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_row_frame)
            else:
                self.player_frame.pack_forget()
        
        # Show default format options
        self.available_formats_label.configure(
            text="Video: 1080p, 720p, 480p, 360p\nAudio: 320kbps, 256kbps, 192kbps, 128kbps"
        )
    
    def _update_spotify_ui(self, formats: dict, track_name: str = None):
        """Update UI for Spotify content."""
        self._current_formats = formats
        
        # Spotify is audio centric
        self.download_type.set("audio")
        self._on_type_change()
        
        if track_name:
            self.audio_title_label.configure(text=f"Spotify: {track_name}")
            self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_row_frame)
            
            # Pre-fill search with track name
            self.spotify_search_entry.delete(0, "end")
            self.spotify_search_entry.insert(0, track_name)
        else:
            self.audio_title_label.configure(text="Spotify detectado - Ingresa nombre para buscar")
            self.player_frame.pack(fill="x", pady=(10, 0), after=self.url_row_frame)
        
        # Show Spotify search input (it's inside info_frame, which is hidden)
        # CRITICAL: If info_frame is hidden, we might need to show the search entry elsewhere
        # For now, let's keep it simple: Spotify always shows its search frame
        self.info_frame.pack(fill="x", pady=(10, 0), after=self.url_row_frame)
        self.spotify_search_frame.pack(fill="x", pady=(5, 0))
        
        self.available_formats_label.configure(
            text="Formatos: MP3, M4A, FLAC, WAV, OGG, OPUS\nSe buscara en YouTube y descargara con yt-dlp"
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
            self.after(0, lambda: self.progress_label.configure(text="Descarga completada"))
            self.after(0, lambda: self._update_status("Descarga completada exitosamente", "success"))
            self.after(0, lambda: self._set_downloading(False))
        elif status == 'error':
            error = progress.get('error', 'Error desconocido')
            self.after(0, lambda: self._update_status(f"Error: {error}", "error"))
            self.after(0, lambda: self._set_downloading(False))
        elif status == 'starting':
            self.after(0, lambda: self.progress_label.configure(
                text=progress.get('message', 'Iniciando...')
            ))
    
    def _set_downloading(self, is_downloading: bool):
        """Set the downloading state."""
        self._is_downloading = is_downloading
        if is_downloading:
            self.download_btn.configure(state="disabled", text="Descargando...")
            self.analyze_btn.configure(state="disabled")
        else:
            self.download_btn.configure(state="normal", text="Descargar")
            self.analyze_btn.configure(state="normal")
    
    def _toggle_playback(self):
        """Toggle audio playback."""
        if not self._preview_file:
            # Need to download first
            self._download_preview()
            return
            
        play_btn = self._active_player_widgets['play_btn'] if self._active_player_widgets else self.play_btn

        if self._preview_playing:
            if PYGAME_LOADED:
                pygame.mixer.music.pause()
            self._preview_playing = False
            self._is_paused = True
            play_btn.configure(text="▶")
        else:
            if PYGAME_LOADED:
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
            play_btn.configure(text="⏸")
            self._update_player_slider()

    def _stop_preview(self):
        """Stop and unload current preview."""
        if PYGAME_LOADED:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except: pass
        
        self._preview_playing = False
        self._is_paused = False
        self._preview_file = None
        self._playback_start_offset = 0
        
        play_btn = self._active_player_widgets['play_btn'] if self._active_player_widgets else self.play_btn
        slider = self._active_player_widgets['slider'] if self._active_player_widgets else self.player_slider
        
        play_btn.configure(text="▶")
        slider.set(0)

    def _seek_audio(self, value):
        """Seek to a position in the audio."""
        if self._preview_file and PYGAME_LOADED:
            duration = self._current_formats.get('duration', 0) if self._current_formats else 30
            if duration == 0: duration = 30 # Fallback for previews
            
            pos = (value / 100) * duration
            self._playback_start_offset = pos
            
            try:
                pygame.mixer.music.play(start=pos)
                if not self._preview_playing:
                    pygame.mixer.music.pause()
                else:
                    self._update_player_slider()
            except:
                pass

    def _update_player_slider(self):
        """Update slider position during playback."""
        if not self._preview_playing or not PYGAME_LOADED:
            return

        if not pygame.mixer.music.get_busy() and self._preview_playing:
            # Finished playing
            self._preview_playing = False
            play_btn = self._active_player_widgets['play_btn'] if self._active_player_widgets else self.play_btn
            play_btn.configure(text="▶")
            self._playback_start_offset = 0
            return

        # get_pos() returns ms since play() was called
        current_ms = pygame.mixer.music.get_pos()
        if current_ms < 0: return
        
        current_sec = self._playback_start_offset + (current_ms / 1000.0)
        duration = self._current_formats.get('duration', 0) if self._current_formats else 30
        if duration == 0: duration = 30
        
        progress = (current_sec / duration) * 100
        
        slider = self._active_player_widgets['slider'] if self._active_player_widgets else self.player_slider
        time_label = self._active_player_widgets['time_label'] if self._active_player_widgets else self.time_label
        
        slider.set(progress)
        
        cur_min, cur_sec = int(current_sec) // 60, int(current_sec) % 60
        dur_min, dur_sec = int(duration) // 60, int(duration) % 60
        time_label.configure(text=f"{cur_min:02d}:{cur_sec:02d} / {dur_min:02d}:{dur_sec:02d}")
        
        if self._preview_playing:
            self.after(500, self._update_player_slider)

    def _show_search_results(self, results):
        """Display search results with expandable rows."""
        for widget in self.results_frame.winfo_children():
            widget.destroy()
            
        if not results:
            ctk.CTkLabel(self.results_frame, text="No se encontraron resultados").pack(pady=10)
            self.results_frame.pack(fill="x", pady=(0, 10), after=self.url_entry.master.master)
            return

        for res in results:
            # Result container
            res_container = ctk.CTkFrame(self.results_frame, fg_color=COLORS["bg_secondary"], corner_radius=6)
            res_container.pack(fill="x", padx=2, pady=3)
            
            # Header row (clickable)
            header = ctk.CTkFrame(res_container, fg_color="transparent", cursor="hand2")
            header.pack(fill="x", padx=8, pady=6)
            
            info_subframe = ctk.CTkFrame(header, fg_color="transparent")
            info_subframe.pack(side="left", fill="x", expand=True)
            
            title = ctk.CTkLabel(
                info_subframe, text=res['title'], 
                font=ctk.CTkFont(size=11, weight="bold"),
                anchor="w", wraplength=350, justify="left"
            )
            title.pack(anchor="w")
            
            dur = res.get('duration', 0)
            dur_str = f"{int(dur)//60}:{int(dur)%60:02d}" if dur else ""
            subtext = ctk.CTkLabel(
                info_subframe, text=f"{res['uploader']} • {dur_str}", 
                font=ctk.CTkFont(size=10), text_color=COLORS["text_secondary"]
            )
            subtext.pack(anchor="w")
            
            # Expanded content (hidden by default)
            body = ctk.CTkFrame(res_container, fg_color=COLORS["bg_tertiary"], corner_radius=4)
            # Won't pack yet
            
            # Integrated components in body
            player_row = ctk.CTkFrame(body, fg_color="transparent")
            player_row.pack(fill="x", padx=10, pady=(8, 4))
            
            # Local widgets for this result
            res_play_btn = ctk.CTkButton(
                player_row, text="▶", width=30, height=28,
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]
            )
            res_play_btn.pack(side="left", padx=(0, 10))
            
            res_slider = ctk.CTkSlider(
                player_row, from_=0, to=100, height=14,
                command=self._seek_audio,
                fg_color=COLORS["bg_dark"], progress_color=COLORS["accent"]
            )
            res_slider.pack(side="left", fill="x", expand=True)
            res_slider.set(0)
            
            res_time_label = ctk.CTkLabel(
                body, text="00:00 / 00:00", font=ctk.CTkFont(size=10),
                text_color=COLORS["text_secondary"]
            )
            res_time_label.pack(anchor="e", padx=10)
            
            # Download button for this specific result
            download_btn = ctk.CTkButton(
                body, text="🚀 DESCARGAR AHORA", height=32,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=COLORS["success"], hover_color="#059669",
                command=lambda r=res: self._download_specific(r)
            )
            download_btn.pack(fill="x", padx=10, pady=(4, 10))

            # Bind events
            res_play_btn.configure(command=lambda r=res, s=res_slider, t=res_time_label, b=res_play_btn: self._preview_result(r, s, t, b))
            header.bind("<Button-1>", lambda e, b=body: self._toggle_row_expansion(b))
            title.bind("<Button-1>", lambda e, b=body: self._toggle_row_expansion(b))
            subtext.bind("<Button-1>", lambda e, b=body: self._toggle_row_expansion(b))

        self.results_frame.pack(fill="x", pady=(0, 10), after=self.url_entry.master.master)
        self._update_status(f"Top 5 resultados", "success")

    def _toggle_row_expansion(self, body_frame):
        """Show or hide the expandable part of a result row, ensuring only one is open."""
        if body_frame.winfo_viewable():
            body_frame.pack_forget()
            self._expanded_row = None
        else:
            # stop existing audio if it's not the one we're opening (or just stop always for simplicity)
            self._stop_preview()
            
            # Hide previous row if any
            if self._expanded_row and self._expanded_row.winfo_exists():
                self._expanded_row.pack_forget()
            
            body_frame.pack(fill="x", padx=8, pady=(0, 8))
            self._expanded_row = body_frame

    def _preview_result(self, result, slider, time_label, play_btn):
        """Start or toggle preview for a specific result."""
        # If this is already the active song, just toggle pause
        if self._download_url == result['url'] and self._preview_file:
            self._toggle_playback()
            return

        # Otherwise, stop current playback and start new
        self._stop_preview()
        
        self._download_url = result['url']
        # Link current widgets
        self._active_player_widgets = {
            'slider': slider,
            'time_label': time_label,
            'play_btn': play_btn
        }
        
        if not self._current_formats:
            self._current_formats = {}
        self._current_formats['duration'] = result['duration']
        
        self._download_preview(result['url'])

    def _download_specific(self, result):
        """Set result as target and START download immediately."""
        try:
            self._update_status("🔄 Seleccionando contenido...", "info")
            self._select_result(result)
            self.update_idletasks() # Refresh UI
            
            mode = self.download_type.get()
            self._update_status(f"🚀 Iniciando {mode}: {result['title'][:30]}...", "success")
            
            # Use after to give UI time to settle
            self.after(200, self._start_download)
        except Exception as e:
            self._update_status(f"Error al iniciar: {str(e)}", "error")

    def _select_result(self, result):
        """Update UI and state for a specific search result."""
        # Ensure entry is normal before editing
        self.url_entry.configure(state="normal")
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, result['url'])
        self._last_analyzed_url = result['url']
        self._download_url = result['url']
        
        # Update current info for download checks (duration, etc)
        self._current_formats = {
            'title': result['title'],
            'uploader': result.get('uploader', 'Unknown'),
            'duration': result.get('duration', 0)
        }
        
        # Update UI info - Don't show global player for search results
        self._update_video_ui_simple(
            result['title'], 
            result.get('uploader', 'Unknown'), 
            result.get('duration', 0),
            show_player=False
        )
        
        # Player is already handled by _update_video_ui_simple or not shown for results

    def _download_preview(self, override_url=None):
        """Download a small piece of audio for preview (Fast)."""
        url = override_url or self._download_url or self.url_entry.get().strip()
        if not url: return
        
        self.play_btn.configure(state="disabled", text="⌛")
        self._update_status("⚡ Cargando avance rápido...", "info")
        
        def do_download():
            try:
                cache_dir = os.path.join(os.getcwd(), ".audio_cache")
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)
                
                # Unique filename per URL to avoid collisions if multiple previews triggered
                import hashlib
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                out_file = os.path.join(cache_dir, f"pre_{url_hash}.mp3")
                
                # Check if already cached
                if not os.path.exists(out_file):
                    import yt_dlp
                    # ULTRA FAST PREVIEW: Download only first few seconds using ffmpeg
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': out_file.replace('.mp3', '.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'external_downloader': 'ffmpeg',
                        'external_downloader_args': {'ffmpeg': ['-t', '30']}, # Only 30 seconds
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '128',
                        }],
                    }
                    
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                
                # The filename might have changed extension before post-processing or after
                actual_file = out_file if os.path.exists(out_file) else None
                if not actual_file:
                    # Look for it in case of extension mismatch
                    for f in os.listdir(cache_dir):
                        if f.startswith(f"pre_{url_hash}") and f.endswith(".mp3"):
                            actual_file = os.path.join(cache_dir, f)
                            break
                
                if actual_file:
                    self._preview_file = actual_file
                    self.after(0, lambda: self._start_playback())
                else:
                    self.after(0, lambda: self._update_status("Error al cargar avance", "error"))
            except Exception as e:
                self.after(0, lambda: self._update_status(f"Error preview: {str(e)}", "error"))
            finally:
                play_btn = self._active_player_widgets['play_btn'] if self._active_player_widgets else self.play_btn
                self.after(0, lambda: play_btn.configure(state="normal", text="▶"))

        threading.Thread(target=do_download, daemon=True).start()

    def _start_playback(self):
        """Start playing the downloaded preview."""
        try:
            if PYGAME_LOADED:
                pygame.mixer.music.load(self._preview_file)
                pygame.mixer.music.play(start=self._playback_start_offset)
                self._preview_playing = True
                self._is_paused = False
                
                play_btn = self._active_player_widgets['play_btn'] if self._active_player_widgets else self.play_btn
                play_btn.configure(text="⏸")
                self._update_player_slider()
                self._update_status("Listo para reproducir", "success")
        except Exception as e:
            self._update_status(f"Error playback: {str(e)}", "error")

    def _start_download(self):
        """Start the download process."""
        url = self.url_entry.get().strip()
        output_path = self.path_entry.get().strip()
        
        if not url:
            self._update_status("Por favor ingresa una URL", "warning")
            return
        
        if not output_path or not os.path.isdir(output_path):
            self._update_status("Por favor selecciona una carpeta válida", "warning")
            return
            
        # Check duration for YouTube if we have it from analysis
        if self._current_formats and detect_url_type(url) == "youtube":
            duration = self._current_formats.get('duration', 0)
            if duration > 1800:
                self._update_status("⚠️ El video de YouTube excede los 30 min", "warning")
                return
        
        # Save path if remember is enabled
        if self.remember_var.get():
            config.set_download_path(output_path)
        
        self._set_downloading(True)
        self.progress_bar.set(0)
        
        def download():
            try:
                self.after(0, lambda: self._update_status("📡 Conectando con el servidor...", "info"))
                url_type = detect_url_type(url)
                quality = self.quality_combo.get()
                format_type = self.format_combo.get()
                download_type = self.download_type.get()
                
                self.after(0, lambda: self._update_status(f"📥 Preparando {download_type} ({quality})...", "info"))
                actual_url = url
                if url_type == "search":
                    actual_url = self._download_url or f"ytsearch1:{url}"
                elif self._playlist_info and self._playlist_info.get('is_playlist'):
                    if self.playlist_choice.get() == "single" and self._download_url:
                        actual_url = self._download_url
                    # else: use original URL for full playlist
                
                if url_type == "spotify":
                    # Spotify download - use search query
                    search_query = self.spotify_search_entry.get().strip()
                    if not search_query:
                        self.after(0, lambda: self._update_status("Ingresa el nombre de la canción", "warning"))
                        self.after(0, lambda: self._set_downloading(False))
                        return
                    
                    success, msg = self.spotify_downloader.download(
                        url, output_path, format_type, quality, search_query
                    )
                    if not success:
                        self.after(0, lambda: self._update_status("Error en la descarga", "error"))
                else:
                    # Video/Audio download
                    download_as_playlist = False
                    if self._playlist_info and self._playlist_info.get('is_playlist'):
                        download_as_playlist = (self.playlist_choice.get() == "playlist")
                    
                    if download_type == "video":
                        success = self.video_downloader.download_video(
                            actual_url, output_path, quality, format_type, 
                            download_as_playlist
                        )
                    else:
                        success = self.video_downloader.download_audio(
                            actual_url, output_path, quality, format_type,
                            download_as_playlist
                        )
                    
                    if not success:
                        self.after(0, lambda: self._update_status("Error en la descarga", "error"))
            
                # Always reset downloading state
                self.after(0, lambda: self._set_downloading(False))
            except Exception as e:
                self.after(0, lambda: self._update_status(f"Error: {str(e)}", "error"))
                self.after(0, lambda: self._set_downloading(False))
        
        threading.Thread(target=download, daemon=True).start()
    


def main():
    """Main entry point."""
    app = UniversalDownloader()
    app.mainloop()


if __name__ == "__main__":
    main()
