import customtkinter as ctk
from src.gui.colors import COLORS
from src.config import config
from tkinter import filedialog
import os

class FormatFrame(ctk.CTkFrame):
    """Format and Quality selectors with Output path config."""
    
    def __init__(self, parent, on_type_change):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=8)
        
        self.on_type_change = on_type_change
        
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)
        
        self.download_type = ctk.StringVar(value="video")
        
        # Selectors Row
        row1 = ctk.CTkFrame(inner, fg_color="transparent")
        row1.pack(fill="x")
        
        self.video_radio = ctk.CTkRadioButton(
            row1, text="▶️", variable=self.download_type, value="video",
            command=self._on_type_change, width=50,
            font=ctk.CTkFont(size=11, weight="bold"), fg_color=COLORS["accent"], border_color=COLORS["accent"]
        )
        self.video_radio.pack(side="left", padx=(0, 8))
        
        self.audio_radio = ctk.CTkRadioButton(
            row1, text="🎵", variable=self.download_type, value="audio",
            command=self._on_type_change, width=50,
            font=ctk.CTkFont(size=11, weight="bold"), fg_color=COLORS["accent"], border_color=COLORS["accent"]
        )
        self.audio_radio.pack(side="left", padx=(0, 15))
        
        # Quality (Remove label, direct combo)
        self.quality_combo = ctk.CTkComboBox(
            row1, values=["Mejor", "1080p", "720p", "480p", "360p"],
            width=95, height=26, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"],
            button_color=COLORS["accent"], dropdown_fg_color=COLORS["bg_tertiary"]
        )
        self.quality_combo.pack(side="left", padx=(0, 10))
        self.quality_combo.set("1080p")
        
        # Format (Remove label, direct combo)
        self.format_combo = ctk.CTkComboBox(
            row1, values=["mp4", "mkv", "webm"],
            width=85, height=26, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"],
            button_color=COLORS["accent"], dropdown_fg_color=COLORS["bg_tertiary"]
        )
        self.format_combo.pack(side="left")
        self.format_combo.set("mp4")

        # Output Path widgets (Remove label)
        self.path_row = ctk.CTkFrame(inner, fg_color="transparent")
        self.path_row.pack(fill="x", pady=(10, 0))
        
        self.path_entry = ctk.CTkEntry(
            self.path_row, height=30, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"], border_width=1
        )
        self.path_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        self.path_entry.insert(0, config.get_download_path())
        
        self.browse_btn = ctk.CTkButton(
            self.path_row, text="Examinar", command=self._browse_folder,
            width=70, height=30, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], hover_color=COLORS["accent"]
        )
        self.browse_btn.pack(side="right")
        
        # Trimming row (Start / End manual config)
        self.trim_row = ctk.CTkFrame(inner, fg_color="transparent")
        self.trim_row.pack(fill="x", pady=(8, 0))
        
        self.trim_var = ctk.BooleanVar(value=False)
        self.trim_check = ctk.CTkCheckBox(
            self.trim_row, text="✂️", variable=self.trim_var,
            font=ctk.CTkFont(size=11, weight="bold"), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16, command=self._toggle_trim_inputs
        )
        self.trim_check.pack(side="left", padx=(0, 10))
        
        self.trim_inputs_frame = ctk.CTkFrame(self.trim_row, fg_color="transparent")
        
        self.start_entry = ctk.CTkEntry(
            self.trim_inputs_frame, placeholder_text="0:00", width=55, height=24, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"], border_width=1
        )
        self.start_entry.pack(side="left")
        self.start_entry.insert(0, "0:00")
        
        ctk.CTkLabel(self.trim_inputs_frame, text="a", font=ctk.CTkFont(size=11)).pack(side="left", padx=5)
        
        self.end_entry = ctk.CTkEntry(
            self.trim_inputs_frame, placeholder_text="0:00", width=55, height=24, font=ctk.CTkFont(size=11),
            fg_color=COLORS["bg_tertiary"], border_color=COLORS["accent"], border_width=1
        )
        self.end_entry.pack(side="left")
        self.end_entry.insert(0, "0:00")
        
        # Grid Options Frame for better spacing
        self.options_grid = ctk.CTkFrame(inner, fg_color="transparent")
        self.options_grid.pack(fill="x", pady=(10, 0))
        
        # Row 0
        self.remember_var = ctk.BooleanVar(value=config.get("remember_location", True))
        self.remember_check = ctk.CTkCheckBox(
            self.options_grid, text="Recordar ubicación",
            variable=self.remember_var, command=self._on_remember_change,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.remember_check.grid(row=0, column=0, sticky="w", pady=(0, 6), padx=(0, 15))
        
        self.always_on_top_var = ctk.BooleanVar(value=config.get("always_on_top", False))
        self.always_on_top_check = ctk.CTkCheckBox(
            self.options_grid, text="Mantener siempre arriba",
            variable=self.always_on_top_var, command=self._toggle_always_on_top,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.always_on_top_check.grid(row=0, column=1, sticky="w", pady=(0, 6))
        
        # Row 1
        self.desktop_var = ctk.BooleanVar(value=False)
        self.desktop_check = ctk.CTkCheckBox(
            self.options_grid, text="Descargar en Escritorio",
            variable=self.desktop_var, command=self._toggle_desktop_path,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.desktop_check.grid(row=1, column=0, sticky="w", pady=(0, 6), padx=(0, 15))
        
        self.clipboard_var = ctk.BooleanVar(value=False)
        self.clipboard_check = ctk.CTkCheckBox(
            self.options_grid, text="Copiar al portapapeles",
            variable=self.clipboard_var,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.clipboard_check.grid(row=1, column=1, sticky="w", pady=(0, 6))
        
        # Row 2
        self.no_audio_var = ctk.BooleanVar(value=False)
        self.no_audio_check = ctk.CTkCheckBox(
            self.options_grid, text="🔇",
            variable=self.no_audio_var,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.no_audio_check.grid(row=2, column=0, sticky="w")
        
        self._saved_user_path = ""

    def _toggle_trim_inputs(self):
        if self.trim_var.get():
            self.trim_inputs_frame.pack(side="left", padx=5)
        else:
            self.trim_inputs_frame.pack_forget()

    def get_trim_range(self):
        """Returns the start and end values if trimming is enabled, else None."""
        if self.trim_var.get():
            return {
                "start": self.start_entry.get().strip() or "0:00",
                "end": self.end_entry.get().strip() or "0:00"
            }
        return None

    def set_trim_values(self, start: str, end: str):
        """Sets start/end times and enables the checkbox."""
        self.trim_var.set(True)
        self._toggle_trim_inputs()
        
        self.start_entry.delete(0, "end")
        self.start_entry.insert(0, start)
        
        self.end_entry.delete(0, "end")
        self.end_entry.insert(0, end)

    def _toggle_desktop_path(self):
        if self.desktop_var.get():
            self._saved_user_path = self.path_entry.get().strip()
            desktop = os.path.join(os.path.expanduser("~"), "Desktop")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, desktop)
            # Temporarily disable entry and browse button to prevent editing
            self.path_entry.configure(state="readonly")
            self.browse_btn.configure(state="disabled")
        else:
            self.path_entry.configure(state="normal")
            self.browse_btn.configure(state="normal")
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, self._saved_user_path or config.get_download_path())

    def is_clipboard_enabled(self) -> bool:
        return self.clipboard_var.get()

    def is_no_audio_enabled(self) -> bool:
        return self.no_audio_var.get()

    def _browse_folder(self):
        folder = filedialog.askdirectory(initialdir=self.path_entry.get() or config.get_download_path())
        if folder:
            self.path_entry.delete(0, "end")
            self.path_entry.insert(0, folder)
            if self.remember_var.get():
                config.set_download_path(folder)

    def _on_remember_change(self):
        config.set("remember_location", self.remember_var.get())
        if self.remember_var.get():
            config.set_download_path(self.path_entry.get())

    def _toggle_always_on_top(self):
        is_on_top = self.always_on_top_var.get()
        self.winfo_toplevel().attributes("-topmost", is_on_top)
        config.set("always_on_top", is_on_top)

    def _on_type_change(self):
        is_video = self.download_type.get() == "video"
        if is_video:
            self.quality_combo.configure(values=["Mejor", "1080p", "720p", "480p", "360p"])
            self.quality_combo.set("1080p")
            self.format_combo.configure(values=["mp4", "mkv", "webm"])
            self.format_combo.set("mp4")
            self.no_audio_check.configure(state="normal")
        else:
            self.quality_combo.configure(values=["320kbps", "256kbps", "192kbps", "128kbps"])
            self.quality_combo.set("320kbps")
            self.format_combo.configure(values=["mp3", "m4a", "wav", "flac"])
            self.format_combo.set("mp3")
            self.no_audio_var.set(False)
            self.no_audio_check.configure(state="disabled")
        self.on_type_change()

    def get_output_path(self) -> str:
        return self.path_entry.get().strip()

    def update_theme_color(self, color: str):
        for radio in [self.video_radio, self.audio_radio]:
            radio.configure(fg_color=color, border_color=color)
        self.quality_combo.configure(border_color=color, button_color=color)
        self.format_combo.configure(border_color=color, button_color=color)
        self.path_entry.configure(border_color=color)
        self.browse_btn.configure(hover_color=color)
        self.remember_check.configure(fg_color=color)
        self.always_on_top_check.configure(fg_color=color)
        self.trim_check.configure(fg_color=color)
        self.start_entry.configure(border_color=color)
        self.end_entry.configure(border_color=color)
        self.desktop_check.configure(fg_color=color)
        self.clipboard_check.configure(fg_color=color)
        self.no_audio_check.configure(fg_color=color)
