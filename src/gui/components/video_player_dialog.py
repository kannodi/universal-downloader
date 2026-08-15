import customtkinter as ctk
import cv2
from PIL import Image
import threading
import time
import os
import sys

# Pygame loading guard
try:
    import pygame
    PYGAME_LOADED = True
except ImportError:
    PYGAME_LOADED = False


class VideoPreviewDialog(ctk.CTkToplevel):
    """Custom popup window playing video files in CustomTkinter using OpenCV, Pillow and Pygame for Audio Sync."""
    
    def __init__(self, parent, video_path: str, title: str = "Vista Previa de Video"):
        super().__init__(parent)
        self.title(title)
        self.geometry("640x510")
        self.configure(fg_color="#0a0a0c")
        self.resizable(False, False)
        
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        self.playing = True
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.frame_delay = int(1000 / self.fps)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 300
        
        # Audio Initialization
        self.audio_loaded = False
        if PYGAME_LOADED:
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(video_path)
                pygame.mixer.music.set_volume(0.8) # Default 80% volume
                pygame.mixer.music.play()
                self.audio_loaded = True
            except Exception as e:
                print(f"Error loading audio: {e}")
        
        self.transient(parent)
        self.grab_set()
        
        self._create_widgets()
        
        # Start reading frames
        self.after(50, self._update_frame)
        self.protocol("WM_DELETE_WINDOW", self._on_closing)
        
    def _create_widgets(self):
        # Video Display Label
        self.video_label = ctk.CTkLabel(self, text="Cargando video...", fg_color="#16161a", corner_radius=8)
        self.video_label.pack(fill="both", expand=True, padx=15, pady=(15, 10))
        
        # Controls Frame
        controls_frame = ctk.CTkFrame(self, fg_color="transparent")
        controls_frame.pack(fill="x", padx=15, pady=(0, 10))
        
        self.play_btn = ctk.CTkButton(
            controls_frame, text="⏸ Pausa", width=80, height=32,
            fg_color="#7c3aed", hover_color="#8b5cf6",
            command=self._toggle_playback
        )
        self.play_btn.pack(side="left")
        
        self.slider = ctk.CTkSlider(
            controls_frame, from_=0, to=100, height=16,
            fg_color="#23232e", progress_color="#7c3aed",
            command=self._seek_video
        )
        self.slider.pack(side="left", fill="x", expand=True, padx=15)
        self.slider.set(0)
        
        self.time_label = ctk.CTkLabel(controls_frame, text="00:00 / 00:00", font=ctk.CTkFont(size=11))
        self.time_label.pack(side="right")

        # Volume and Trimming Controls Row
        volume_frame = ctk.CTkFrame(self, fg_color="transparent")
        volume_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(volume_frame, text="🔊 Vol:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(0, 5))
        
        self.volume_slider = ctk.CTkSlider(
            volume_frame, from_=0, to=1, height=14, width=100,
            fg_color="#23232e", progress_color="#7c3aed",
            command=self._set_volume
        )
        self.volume_slider.pack(side="left")
        self.volume_slider.set(0.8)
        
        # Trim Controls
        ctk.CTkLabel(volume_frame, text="⏱ Recortar:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(25, 5))
        
        self.start_entry = ctk.CTkEntry(
            volume_frame, placeholder_text="0:00", width=60, height=26, font=ctk.CTkFont(size=11),
            fg_color="#16161a", border_color="#23232e", border_width=1
        )
        self.start_entry.pack(side="left")
        self.start_entry.insert(0, "0:00")
        
        ctk.CTkLabel(volume_frame, text="a", font=ctk.CTkFont(size=11)).pack(side="left", padx=5)
        
        tot_sec = int(self.total_frames / self.fps)
        total_time_str = f"{tot_sec//60}:{tot_sec%60:02d}"
        
        self.end_entry = ctk.CTkEntry(
            volume_frame, placeholder_text=total_time_str, width=60, height=26, font=ctk.CTkFont(size=11),
            fg_color="#16161a", border_color="#23232e", border_width=1
        )
        self.end_entry.pack(side="left")
        self.end_entry.insert(0, total_time_str)
        
        self.confirm_btn = ctk.CTkButton(
            volume_frame, text="✓ Confirmar", width=80, height=26, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color="#10b981", hover_color="#059669",
            command=self._confirm_trim
        )
        self.confirm_btn.pack(side="right", padx=(10, 0))
        
    def _update_frame(self):
        if not self.cap.isOpened() or not self.winfo_exists():
            return
            
        if self.playing:
            # Sync frame read based on Pygame music elapsed time (for better audio-video synchronization)
            if self.audio_loaded:
                current_ms = pygame.mixer.music.get_pos()
                if current_ms >= 0:
                    target_frame = int((current_ms / 1000.0) * self.fps)
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            ret, frame = self.cap.read()
            if ret:
                w, h = 600, 340
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                self.video_label.configure(image=ctk_img, text="")
                
                # Update slider position and time labels
                current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                msec = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                
                progress = (current_frame / self.total_frames) * 100
                self.slider.set(progress)
                
                cur_sec = int(msec / 1000)
                tot_sec = int(self.total_frames / self.fps)
                self.time_label.configure(
                    text=f"{cur_sec//60:02d}:{cur_sec%60:02d} / {tot_sec//60:02d}:{tot_sec%60:02d}"
                )
            else:
                # End of video: loop back to start
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                if self.audio_loaded:
                    pygame.mixer.music.play()
                
        self.after(self.frame_delay, self._update_frame)
        
    def _toggle_playback(self):
        self.playing = not self.playing
        if self.playing:
            self.play_btn.configure(text="⏸ Pausa")
            if self.audio_loaded:
                pygame.mixer.music.unpause()
        else:
            self.play_btn.configure(text="▶ Reproducir")
            if self.audio_loaded:
                pygame.mixer.music.pause()
            
    def _seek_video(self, value):
        if self.cap.isOpened():
            target_frame = int((float(value) / 100) * self.total_frames)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # Seek audio position
            if self.audio_loaded:
                pos_sec = target_frame / self.fps
                try:
                    pygame.mixer.music.play(start=pos_sec)
                    if not self.playing:
                        pygame.mixer.music.pause()
                except:
                    pass
            
            if not self.playing:
                ret, frame = self.cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(600, 340))
                    self.video_label.configure(image=ctk_img, text="")
                    
    def _set_volume(self, value):
        if self.audio_loaded:
            pygame.mixer.music.set_volume(float(value))

    def _confirm_trim(self):
        start_str = self.start_entry.get().strip()
        end_str = self.end_entry.get().strip()
        
        def parse_time(time_str):
            try:
                parts = time_str.split(':')
                if len(parts) == 2:
                    return int(parts[0]) * 60 + int(parts[1])
                elif len(parts) == 3:
                    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                return int(time_str)
            except:
                return None
                
        start_sec = parse_time(start_str)
        end_sec = parse_time(end_str)
        
        if start_sec is None or end_sec is None:
            self.confirm_btn.configure(text="Formato inválido", fg_color="#ef4444")
            self.after(2000, lambda: self.confirm_btn.configure(text="✓ Confirmar", fg_color="#10b981"))
            return
            
        tot_sec = int(self.total_frames / self.fps)
        if start_sec < 0 or end_sec > tot_sec or start_sec >= end_sec:
            self.confirm_btn.configure(text="Rango inválido", fg_color="#ef4444")
            self.after(2000, lambda: self.confirm_btn.configure(text="✓ Confirmar", fg_color="#10b981"))
            return
            
        # Call controller setter
        if hasattr(self.master, "controller"):
            self.master.controller.set_trim_range(start_str, end_str)
            
        self.confirm_btn.configure(text="✓ Confirmado!", fg_color="#10b981")
        self.after(1500, self._on_closing)

    def _on_closing(self):
        self.playing = False
        if self.audio_loaded:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except:
                pass
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()
