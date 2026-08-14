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

        # Output Path widgets
        self.path_row = ctk.CTkFrame(inner, fg_color="transparent")
        self.path_row.pack(fill="x", pady=(10, 0))
        
        ctk.CTkLabel(self.path_row, text="Ruta:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 5))
        
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
        
        # Options row
        options_row = ctk.CTkFrame(inner, fg_color="transparent")
        options_row.pack(fill="x", pady=(8, 0))
        
        self.remember_var = ctk.BooleanVar(value=config.get("remember_location", True))
        self.remember_check = ctk.CTkCheckBox(
            options_row, text="Recordar ubicación",
            variable=self.remember_var, command=self._on_remember_change,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.remember_check.pack(side="left")
        
        self.always_on_top_var = ctk.BooleanVar(value=config.get("always_on_top", False))
        self.always_on_top_check = ctk.CTkCheckBox(
            options_row, text="Mantener siempre arriba",
            variable=self.always_on_top_var, command=self._toggle_always_on_top,
            font=ctk.CTkFont(size=11), fg_color=COLORS["accent"],
            checkbox_height=16, checkbox_width=16
        )
        self.always_on_top_check.pack(side="left", padx=(20, 0))

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
        else:
            self.quality_combo.configure(values=["320kbps", "256kbps", "192kbps", "128kbps"])
            self.quality_combo.set("320kbps")
            self.format_combo.configure(values=["mp3", "m4a", "wav", "flac"])
            self.format_combo.set("mp3")
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
