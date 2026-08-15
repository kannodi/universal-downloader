import customtkinter as ctk
import cv2
from PIL import Image
import threading
import time

class VideoPreviewDialog(ctk.CTkToplevel):
    """Custom popup window playing video files in CustomTkinter using OpenCV and Pillow."""
    
    def __init__(self, parent, video_path: str, title: str = "Vista Previa de Video"):
        super().__init__(parent)
        self.title(title)
        self.geometry("640x480")
        self.configure(fg_color="#0a0a0c")
        self.resizable(False, False)
        
        self.video_path = video_path
        self.cap = cv2.VideoCapture(video_path)
        
        self.playing = True
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        self.frame_delay = int(1000 / self.fps)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT)) or 300
        
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
        controls_frame.pack(fill="x", padx=15, pady=(0, 15))
        
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
        
    def _update_frame(self):
        if not self.cap.isOpened() or not self.winfo_exists():
            return
            
        if self.playing:
            ret, frame = self.cap.read()
            if ret:
                # Video dimensions
                w, h = 600, 340
                
                # Convert OpenCV BGR to Pillow RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                
                # Create CTkImage scaled correctly
                ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(w, h))
                
                self.video_label.configure(image=ctk_img, text="")
                
                # Update slider position and time labels
                current_frame = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))
                msec = self.cap.get(cv2.CAP_PROP_POS_MSEC)
                
                progress = (current_frame / self.total_frames) * 100
                self.slider.set(progress)
                
                # Time label calculations
                cur_sec = int(msec / 1000)
                tot_sec = int(self.total_frames / self.fps)
                
                self.time_label.configure(
                    text=f"{cur_sec//60:02d}:{cur_sec%60:02d} / {tot_sec//60:02d}:{tot_sec%60:02d}"
                )
            else:
                # End of video: loop back to start
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                
        # Schedule next frame update
        self.after(self.frame_delay, self._update_frame)
        
    def _toggle_playback(self):
        self.playing = not self.playing
        if self.playing:
            self.play_btn.configure(text="⏸ Pausa")
        else:
            self.play_btn.configure(text="▶ Reproducir")
            
    def _seek_video(self, value):
        if self.cap.isOpened():
            # Go to specific frame based on slider %
            target_frame = int((float(value) / 100) * self.total_frames)
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
            
            # Read single frame to update visual immediately if paused
            if not self.playing:
                ret, frame = self.cap.read()
                if ret:
                    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    img = Image.fromarray(frame_rgb)
                    ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=(600, 340))
                    self.video_label.configure(image=ctk_img, text="")
                    
    def _on_closing(self):
        self.playing = False
        if self.cap.isOpened():
            self.cap.release()
        self.destroy()
