import customtkinter as ctk
from src.gui.colors import COLORS

class UrlFrame(ctk.CTkFrame):
    """Url Input Frame with Analyze and Download Actions."""
    
    def __init__(self, parent, on_analyze, on_download, on_paste):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=8)
        
        self.on_analyze = on_analyze
        self.on_download = on_download
        
        inner = ctk.CTkFrame(self, fg_color="transparent")
        inner.pack(fill="x", padx=10, pady=8)
        
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")
        
        self.url_entry = ctk.CTkEntry(
            row,
            placeholder_text="Pega URL de YouTube, Spotify u otro sitio...",
            height=32,
            font=ctk.CTkFont(size=12),
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["accent"],
            border_width=1
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        
        # Bind events
        self.url_entry.bind("<Control-v>", lambda e: parent.after(100, on_paste))
        self.url_entry.bind("<<Paste>>", lambda e: parent.after(100, on_paste))
        self.url_entry.bind("<Return>", lambda e: on_analyze())
        
        self.analyze_btn = ctk.CTkButton(
            row,
            text="🔍",
            command=on_analyze,
            width=40,
            height=32,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        )
        self.analyze_btn.pack(side="right", padx=(5, 0))

        self.download_btn = ctk.CTkButton(
            row,
            text="📥",
            command=on_download,
            width=40,
            height=32,
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"]
        )
        self.download_btn.pack(side="right", padx=(5, 0))

    def get_url(self) -> str:
        return self.url_entry.get().strip()

    def set_url(self, url: str):
        self.url_entry.configure(state="normal")
        self.url_entry.delete(0, "end")
        self.url_entry.insert(0, url)

    def set_analyzing(self, analyzing: bool):
        if analyzing:
            self.analyze_btn.configure(state="disabled", text="⌛")
        else:
            self.analyze_btn.configure(state="normal", text="🔍")

    def set_downloading(self, downloading: bool):
        if downloading:
            self.download_btn.configure(state="disabled", text="⌛")
            self.analyze_btn.configure(state="disabled")
        else:
            self.download_btn.configure(state="normal", text="📥")
            self.analyze_btn.configure(state="normal")

    def update_theme_color(self, color: str):
        self.url_entry.configure(border_color=color)
        self.analyze_btn.configure(fg_color=color, hover_color=color)
        self.download_btn.configure(fg_color=color, hover_color=color)
