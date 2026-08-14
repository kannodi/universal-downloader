import customtkinter as ctk
from src.gui.colors import COLORS

class SearchResults(ctk.CTkScrollableFrame):
    """Scrollable lists showing search results with expandable player and download row."""
    
    def __init__(self, parent, on_preview_result, on_download_specific):
        super().__init__(parent, fg_color=COLORS["bg_secondary"], corner_radius=8, height=120)
        self.on_preview_result = on_preview_result
        self.on_download_specific = on_download_specific
        self._expanded_row = None
        self.active_widgets = None

    def display_results(self, results):
        for widget in self.winfo_children():
            widget.destroy()
            
        if not results:
            ctk.CTkLabel(self, text="No se encontraron resultados").pack(pady=10)
            return

        for res in results:
            res_container = ctk.CTkFrame(self, fg_color=COLORS["bg_secondary"], corner_radius=6)
            res_container.pack(fill="x", padx=2, pady=3)
            
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
            
            body = ctk.CTkFrame(res_container, fg_color=COLORS["bg_tertiary"], corner_radius=4)
            
            player_row = ctk.CTkFrame(body, fg_color="transparent")
            player_row.pack(fill="x", padx=10, pady=(8, 4))
            
            res_play_btn = ctk.CTkButton(
                player_row, text="▶", width=30, height=28,
                fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"]
            )
            res_play_btn.pack(side="left", padx=(0, 10))
            
            res_slider = ctk.CTkSlider(
                player_row, from_=0, to=100, height=14,
                fg_color=COLORS["bg_dark"], progress_color=COLORS["accent"]
            )
            res_slider.pack(side="left", fill="x", expand=True)
            res_slider.set(0)
            
            res_time_label = ctk.CTkLabel(
                body, text="00:00 / 00:00", font=ctk.CTkFont(size=10),
                text_color=COLORS["text_secondary"]
            )
            res_time_label.pack(anchor="e", padx=10)
            
            download_btn = ctk.CTkButton(
                body, text="🚀 DESCARGAR AHORA", height=32,
                font=ctk.CTkFont(size=11, weight="bold"),
                fg_color=COLORS["success"], hover_color="#059669",
                command=lambda r=res: self.on_download_specific(r)
            )
            download_btn.pack(fill="x", padx=10, pady=(4, 10))
            
            # Setup callbacks
            res_play_btn.configure(command=lambda r=res, s=res_slider, t=res_time_label, b=res_play_btn: self._preview(r, s, t, b))
            
            # Toggle expansion bindings
            for widget in [header, title, subtext]:
                widget.bind("<Button-1>", lambda e, b=body: self._toggle_row_expansion(b))

    def _toggle_row_expansion(self, body_frame):
        if body_frame.winfo_viewable():
            body_frame.pack_forget()
            self._expanded_row = None
        else:
            if self._expanded_row and self._expanded_row.winfo_exists():
                self._expanded_row.pack_forget()
            body_frame.pack(fill="x", padx=8, pady=(0, 8))
            self._expanded_row = body_frame

    def _preview(self, result, slider, time_label, play_btn):
        self.active_widgets = {
            'slider': slider,
            'time_label': time_label,
            'play_btn': play_btn
        }
        self.on_preview_result(result, slider, time_label, play_btn)
