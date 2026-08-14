import customtkinter as ctk
from src.gui.colors import COLORS

class PlayerFrame(ctk.CTkFrame):
    """Mini audio player with playback control and seek bar."""
    
    def __init__(self, parent, on_toggle_playback, on_seek):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=8)
        
        self.on_toggle_playback = on_toggle_playback
        self.on_seek = on_seek
        
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", padx=10, pady=8)

        self.audio_title_label = ctk.CTkLabel(
            container, text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=COLORS["text_primary"],
            wraplength=400
        )
        self.audio_title_label.pack(anchor="w", pady=(0, 5))
        
        player_row = ctk.CTkFrame(container, fg_color="transparent")
        player_row.pack(fill="x")
        
        self.play_btn = ctk.CTkButton(
            player_row, text="▶", width=30, height=30,
            command=self.on_toggle_playback,
            fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]
        )
        self.play_btn.pack(side="left", padx=(0, 10))
        
        self.player_slider = ctk.CTkSlider(
            player_row, from_=0, to=100, height=16,
            command=self.on_seek,
            fg_color=COLORS["bg_tertiary"], progress_color=COLORS["accent"]
        )
        self.player_slider.pack(side="left", fill="x", expand=True)
        self.player_slider.set(0)
        
        self.time_label = ctk.CTkLabel(
            self, text="00:00 / 00:00",
            font=ctk.CTkFont(size=10), text_color=COLORS["text_secondary"]
        )
        self.time_label.pack(anchor="e", padx=10, pady=(0, 4))

    def set_audio_title(self, title: str):
        self.audio_title_label.configure(text=title)

    def set_play_btn_text(self, text: str):
        self.play_btn.configure(text=text)

    def set_play_btn_state(self, state: str):
        self.play_btn.configure(state=state)

    def set_slider_value(self, progress: float):
        self.player_slider.set(progress)

    def update_time_label(self, text: str):
        self.time_label.configure(text=text)

    def update_theme_color(self, color: str):
        self.play_btn.configure(fg_color=color, hover_color=color)
        self.player_slider.configure(progress_color=color)
