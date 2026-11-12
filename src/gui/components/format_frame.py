import customtkinter as ctk
from src.gui.colors import COLORS
from src.config import config
from tkinter import filedialog
import os

class FormatFrame(ctk.CTkFrame):
    """Format and Quality selectors with a minimalist layout."""

    def __init__(self, parent, on_type_change):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=8)

        self.on_type_change = on_type_change

        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=15, pady=12)

        self.download_type = ctk.StringVar(value=config.get("download_type", "video"))
        is_video = self.download_type.get() == "video"

        # 1. Segmented Button for Type (Replaces Radio Buttons)
        self.type_seg = ctk.CTkSegmentedButton(
            inner, values=["🎬 Video", "🎵 Audio"],
            command=self._on_type_change_seg,
            font=ctk.CTkFont(size=12, weight="bold"),
            selected_color=COLORS["accent"],
            selected_hover_color=COLORS["accent"],
            unselected_color=COLORS["bg_tertiary"],
            unselected_hover_color=COLORS["bg_tertiary"]
        )
        self.type_seg.pack(fill="x", pady=(0, 12))
        self.type_seg.set("🎬 Video" if is_video else "🎵 Audio")

        # 2. Quality and Format Row
        combo_row = ctk.CTkFrame(inner, fg_color="transparent")
        combo_row.pack(fill="x", pady=(0, 12))

        quality_values = ["Mejor", "1080p", "720p", "480p", "360p"] if is_video else ["320kbps", "256kbps", "192kbps", "128kbps"]
        saved_quality = config.get("last_video_quality" if is_video else "last_audio_quality", "1080p" if is_video else "320kbps")

        self.quality_combo = ctk.CTkComboBox(
            combo_row, values=quality_values,
            height=30, font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_tertiary"], border_color="gray20",
            button_color="gray20", dropdown_fg_color=COLORS["bg_tertiary"],
            command=self._on_quality_change
        )
        self.quality_combo.pack(side="left", expand=True, fill="x", padx=(0, 10))
        self.quality_combo.set(saved_quality if saved_quality in quality_values else quality_values[0])

        format_values = ["mp4", "mkv", "webm"] if is_video else ["mp3", "m4a", "wav", "flac"]
        saved_format = config.get("last_video_format" if is_video else "last_audio_format", "mp4" if is_video else "mp3")

        self.format_combo = ctk.CTkComboBox(
            combo_row, values=format_values,
            height=30, font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_tertiary"], border_color="gray20",
            button_color="gray20", dropdown_fg_color=COLORS["bg_tertiary"],
            command=self._on_format_change
        )
        self.format_combo.pack(side="right", expand=True, fill="x")
        self.format_combo.set(saved_format if saved_format in format_values else format_values[0])

        # 3. Output Path & Advanced Settings Toggle
        path_row = ctk.CTkFrame(inner, fg_color="transparent")
        path_row.pack(fill="x")

        self._current_path = config.get_download_path()
        self.browse_btn = ctk.CTkButton(
            path_row, text=self._format_path_text(self._current_path), command=self._browse_folder,
            height=30, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], hover_color="gray20", anchor="w"
        )
        self.browse_btn.pack(side="left", fill="x", expand=True)

        self.advanced_btn = ctk.CTkButton(
            path_row, text="⚙️", width=36, height=30, command=self._toggle_advanced,
            fg_color="transparent", hover_color="gray20"
        )
        self.advanced_btn.pack(side="right", padx=(10, 0))

        # ==========================================
        # 4. Advanced Settings Frame (Hidden by default)
        # ==========================================
        self.advanced_frame = ctk.CTkFrame(inner, fg_color=COLORS.get("bg_tertiary", "gray15"), corner_radius=6)
        self._is_advanced_open = False

        # Checkboxes grid inside advanced
        options_grid = ctk.CTkFrame(self.advanced_frame, fg_color="transparent")
        options_grid.pack(fill="x", padx=10, pady=10)

        # Checkbox variables
        self.remember_var = ctk.BooleanVar(value=config.get("remember_location", True))
        self.always_on_top_var = ctk.BooleanVar(value=config.get("always_on_top", False))
        self.desktop_var = ctk.BooleanVar(value=config.get("desktop_destination", False))
        self.clipboard_var = ctk.BooleanVar(value=config.get("copy_to_clipboard", False))
        self.no_audio_var = ctk.BooleanVar(value=config.get("mute_video", False) if is_video else False)

        # Row 0
        self.remember_check = self._create_checkbox(options_grid, "Recordar ubicación", self.remember_var, self._on_remember_change)
        self.remember_check.grid(row=0, column=0, sticky="w", pady=(0, 6), padx=(0, 15))

        self.always_on_top_check = self._create_checkbox(options_grid, "Siempre arriba", self.always_on_top_var, self._toggle_always_on_top)
        self.always_on_top_check.grid(row=0, column=1, sticky="w", pady=(0, 6))

        # Row 1
        self.desktop_check = self._create_checkbox(options_grid, "Descargar en Escritorio", self.desktop_var, self._toggle_desktop_path)
        self.desktop_check.grid(row=1, column=0, sticky="w", pady=(0, 6), padx=(0, 15))

        self.clipboard_check = self._create_checkbox(options_grid, "Copiar al portapapeles", self.clipboard_var, self._on_clipboard_change)
        self.clipboard_check.grid(row=1, column=1, sticky="w", pady=(0, 6))

        # Row 2 (Cookies & Mute)
        self.no_audio_check = self._create_checkbox(options_grid, "🔇 Sin audio", self.no_audio_var, self._on_no_audio_change)
        self.no_audio_check.grid(row=2, column=0, sticky="w", pady=(0, 6), padx=(0, 15))
        if not is_video:
            self.no_audio_check.configure(state="disabled")

        cookies_row = ctk.CTkFrame(options_grid, fg_color="transparent")
        cookies_row.grid(row=2, column=1, sticky="w", pady=(0, 6))
        ctk.CTkLabel(cookies_row, text="🍪", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 5))
        browsers = ["none", "chrome", "firefox", "edge", "brave", "opera", "vivaldi"]
        self.browser_combo = ctk.CTkComboBox(
            cookies_row, values=browsers,
            width=90, height=20, font=ctk.CTkFont(size=10),
            fg_color="gray20", border_width=0, button_color="gray25",
            command=self._on_browser_change
        )
        self.browser_combo.pack(side="left")
        self.browser_combo.set(config.get("browser_cookies", "none"))

        # Row 3 (Trim)
        trim_row = ctk.CTkFrame(options_grid, fg_color="transparent")
        trim_row.grid(row=3, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.trim_var = ctk.BooleanVar(value=False)
        self.trim_check = self._create_checkbox(trim_row, "✂️ Recortar", self.trim_var, self._toggle_trim_inputs)
        self.trim_check.pack(side="left", padx=(0, 10))

        self.trim_inputs_frame = ctk.CTkFrame(trim_row, fg_color="transparent")
        self.start_entry = ctk.CTkEntry(self.trim_inputs_frame, placeholder_text="0:00", width=45, height=22, font=ctk.CTkFont(size=11))
        self.start_entry.pack(side="left")
        self.start_entry.insert(0, "0:00")
        ctk.CTkLabel(self.trim_inputs_frame, text="-", font=ctk.CTkFont(size=11)).pack(side="left", padx=3)
        self.end_entry = ctk.CTkEntry(self.trim_inputs_frame, placeholder_text="0:00", width=45, height=22, font=ctk.CTkFont(size=11))
        self.end_entry.pack(side="left")
        self.end_entry.insert(0, "0:00")

        self._saved_user_path = ""
        if self.desktop_var.get():
            self._toggle_desktop_path()

    def _create_checkbox(self, parent, text, var, cmd):
        return ctk.CTkCheckBox(
            parent, text=text, variable=var, command=cmd,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=14, checkbox_width=14, border_width=2
        )

    def _format_path_text(self, full_path):
        """Returns a nicely formatted truncated path."""
        basename = os.path.basename(full_path)
        if not basename:
            basename = full_path
        return f"📂 {basename}"

    def _toggle_advanced(self):
        if self._is_advanced_open:
            self.advanced_frame.pack_forget()
            self._is_advanced_open = False
        else:
            self.advanced_frame.pack(fill="x", pady=(10, 0))
            self._is_advanced_open = True

    def _on_type_change_seg(self, value):
        is_video = value == "🎬 Video"
        self.download_type.set("video" if is_video else "audio")
        config.set("download_type", "video" if is_video else "audio")

        if is_video:
            self.quality_combo.configure(values=["Mejor", "1080p", "720p", "480p", "360p"])
            self.quality_combo.set(config.get("last_video_quality", "1080p"))
            self.format_combo.configure(values=["mp4", "mkv", "webm"])
            self.format_combo.set(config.get("last_video_format", "mp4"))
            self.no_audio_var.set(config.get("mute_video", False))
            self.no_audio_check.configure(state="normal")
        else:
            self.quality_combo.configure(values=["320kbps", "256kbps", "192kbps", "128kbps"])
            self.quality_combo.set(config.get("last_audio_quality", "320kbps"))
            self.format_combo.configure(values=["mp3", "m4a", "wav", "flac"])
            self.format_combo.set(config.get("last_audio_format", "mp3"))
            self.no_audio_var.set(False)
            self.no_audio_check.configure(state="disabled")
        self.on_type_change()

    def _toggle_trim_inputs(self):
        if self.trim_var.get():
            self.trim_inputs_frame.pack(side="left", padx=5)
        else:
            self.trim_inputs_frame.pack_forget()

    def get_trim_range(self):
        if self.trim_var.get():
            return {
                "start": self.start_entry.get().strip() or "0:00",
                "end": self.end_entry.get().strip() or "0:00"
            }
        return None

    def set_trim_values(self, start: str, end: str):
        self.trim_var.set(True)
        self._toggle_trim_inputs()
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, start)
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, end)

    def _toggle_desktop_path(self):
        is_desktop = self.desktop_var.get()
        config.set("desktop_destination", is_desktop)
        if is_desktop:
            self._saved_user_path = self._current_path
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            self._current_path = desktop
            self.browse_btn.configure(text=self._format_path_text(desktop), state="disabled")
        else:
            self._current_path = self._saved_user_path or config.get_download_path()
            self.browse_btn.configure(text=self._format_path_text(self._current_path), state="normal")

    def _on_clipboard_change(self):
        config.set("copy_to_clipboard", self.clipboard_var.get())

    def _on_no_audio_change(self):
        config.set("mute_video", self.no_audio_var.get())

    def _on_browser_change(self, value: str):
        config.set("browser_cookies", value)

    def _on_quality_change(self, value: str):
        is_video = self.download_type.get() == "video"
        config.set("last_video_quality" if is_video else "last_audio_quality", value)

    def _on_format_change(self, value: str):
        is_video = self.download_type.get() == "video"
        config.set("last_video_format" if is_video else "last_audio_format", value)

    def is_clipboard_enabled(self) -> bool:
        return self.clipboard_var.get()

    def is_no_audio_enabled(self) -> bool:
        return self.no_audio_var.get()

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self._current_path)
        if folder:
            self._current_path = folder
            self.browse_btn.configure(text=self._format_path_text(folder))
            if self.remember_var.get():
                config.set_download_path(folder)

    def _on_remember_change(self):
        config.set("remember_location", self.remember_var.get())
        if self.remember_var.get():
            config.set_download_path(self._current_path)

    def _toggle_always_on_top(self):
        is_on_top = self.always_on_top_var.get()
        self.winfo_toplevel().attributes("-topmost", is_on_top)
        config.set("always_on_top", is_on_top)

    def get_output_path(self) -> str:
        return self._current_path

    def update_theme_color(self, color: str):
        self.type_seg.configure(selected_color=color, selected_hover_color=color)
        self.remember_check.configure(fg_color=color)
        self.always_on_top_check.configure(fg_color=color)
        self.trim_check.configure(fg_color=color)
        self.desktop_check.configure(fg_color=color)
        self.clipboard_check.configure(fg_color=color)
        self.no_audio_check.configure(fg_color=color)
