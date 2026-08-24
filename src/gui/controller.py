import threading
import os
import hashlib
try:
    import pygame
    PYGAME_LOADED = True
except ImportError:
    PYGAME_LOADED = False
from typing import Optional, Callable, Dict
import yt_dlp
from src.video_downloader import VideoDownloader, detect_url_type
from src.spotify_downloader import SpotifyDownloader

class DownloadController:
    """Handles threading, audio playback, preview downloads, and main downloads asynchronously."""
    
    def __init__(self, ui):
        self.ui = ui
        self.video_downloader = VideoDownloader(progress_callback=self._on_progress)
        self.spotify_downloader = SpotifyDownloader(progress_callback=self._on_progress)
        
        # Concurrency & Playback state
        self._is_analyzing = False
        self._is_downloading = False
        self._preview_playing = False
        self._preview_file = None
        self._playback_start_offset = 0
        self._is_paused = False
        self._active_widgets = None
        self._current_formats = {}
        self._playlist_info = None
        self._download_url = None
        self._last_analyzed_url = None
        self._trim_range = None

    def set_trim_range(self, start: str, end: str):
        """Sets the selected trim range to apply during final download."""
        self._trim_range = {"start": start, "end": end}
        self.ui.format_frame.set_trim_values(start, end)
        self.ui._update_status(f"Recorte guardado: {start} a {end}", "success")

    def open_video_preview(self):
        """Downloads a preview of the video and launches the custom VideoPreviewDialog (or plays audio inline if audio mode)."""
        url = self._download_url or self.ui.url_frame.get_url()
        if not url: return
        
        # If download type is Audio, play audio inline instead of opening the video dialog
        if self.ui.format_frame.download_type.get() == "audio":
            self.download_preview(url)
            return
            
        self.ui._update_status("⚡ Descargando vista previa de video...", "info")
        self.ui.open_video_btn.configure(state="disabled")
        
        def run_preview_download():
            try:
                cache_dir = os.path.join(os.getcwd(), ".video_cache")
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)
                    
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                temp_video = os.path.join(cache_dir, f"vid_{url_hash}.mp4")
                
                if not os.path.exists(temp_video):
                    # Downloader options for worst quality (lightweight) full file
                    ydl_opts = {
                        'format': 'worstvideo[ext=mp4]+worstaudio/worst[ext=mp4]/worst',
                        'outtmpl': temp_video.replace('.mp4', '.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                
                # Retrieve actual output filename
                actual_file = temp_video if os.path.exists(temp_video) else None
                if not actual_file:
                    for f in os.listdir(cache_dir):
                        if f.startswith(f"vid_{url_hash}") and f.endswith(".mp4"):
                            actual_file = os.path.join(cache_dir, f)
                            break
                            
                if actual_file:
                    self.ui.after(0, lambda: self.ui._update_status("Listo para reproducir", "success"))
                    # Launch pop-up dialog
                    from src.gui.components.video_player_dialog import VideoPreviewDialog
                    self.ui.after(0, lambda f=actual_file: VideoPreviewDialog(self.ui, f))
                else:
                    self.ui.after(0, lambda: self.ui._update_status("Error al descargar vista previa", "error"))
            except Exception as e:
                self.ui.after(0, lambda: self.ui._update_status(f"Error preview: {str(e)}", "error"))
            finally:
                self.ui.after(0, lambda: self.ui.open_video_btn.configure(state="normal"))

        threading.Thread(target=run_preview_download, daemon=True).start()

    def _on_progress(self, progress: dict):
        status = progress.get('status', '')
        if status == 'downloading':
            percent = progress.get('percent', 0)
            self.ui.after(0, lambda: self.ui.progress_bar.set(percent / 100))
            self.ui.after(0, lambda: self.ui.progress_label.configure(
                text=f"Descargando... {percent:.1f}%"
            ))
        elif status == 'finished':
            self.ui.after(0, lambda: self.ui.progress_bar.set(1))
            self.ui.after(0, lambda: self.ui.progress_label.configure(text="Descarga completada"))
            
            # Copy to clipboard if enabled
            filename = progress.get('filename')
            if filename and os.path.exists(filename) and self.ui.format_frame.is_clipboard_enabled():
                def copy_file_to_clipboard(file_path):
                    try:
                        # PowerShell script to copy a file object to clipboard
                        abs_path = os.path.abspath(file_path)
                        cmd = f"powershell -NoProfile -Command \"Set-Clipboard -Path '{abs_path}'\""
                        import subprocess
                        subprocess.run(cmd, shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        self.ui.after(0, lambda: self.ui._update_status("Descarga completada y copiada al portapapeles", "success"))
                    except Exception as e:
                        print(f"Error copying to clipboard: {e}")
                        self.ui.after(0, lambda: self.ui._update_status("Descarga completada (error al copiar portapapeles)", "warning"))
                
                threading.Thread(target=copy_file_to_clipboard, args=(filename,), daemon=True).start()
            else:
                self.ui.after(0, lambda: self.ui._update_status("Descarga completada exitosamente", "success"))
                
            self.ui.after(0, lambda: self._set_downloading(False))
        elif status == 'error':
            error = progress.get('error', 'Error desconocido')
            self.ui.after(0, lambda: self.ui._update_status(f"Error: {error}", "error"))
            self.ui.after(0, lambda: self._set_downloading(False))
        elif status == 'starting':
            self.ui.after(0, lambda: self.ui.progress_label.configure(
                text=progress.get('message', 'Iniciando...')
            ))

    def _set_downloading(self, is_downloading: bool):
        self._is_downloading = is_downloading
        self.ui.after(0, lambda: self.ui.url_frame.set_downloading(is_downloading))

    def analyze_url(self):
        url = self.ui.url_frame.get_url()
        if not url:
            self.ui._update_status("Por favor ingresa una URL", "warning")
            return
            
        if url == self._last_analyzed_url or self._is_analyzing:
            return
            
        self._is_analyzing = True
        self._last_analyzed_url = url
        self.ui.url_frame.set_analyzing(True)
        self.ui._update_status("🔍 Analizando URL...", "info")
        
        self._active_widgets = None
        self._playlist_info = None
        self._download_url = url
        
        # Clear UI components
        self.ui.playlist_frame.pack_forget()
        self.ui.spotify_search_frame.pack_forget()
        self.ui.player_frame.pack_forget()
        self.ui.results_frame.pack_forget()
        self.ui.info_frame.pack_forget()
        self.stop_preview()

        def analyze():
            try:
                url_type = detect_url_type(url)
                if url_type == "invalid":
                    self.ui.after(0, lambda: self.ui._update_status("URL no válida", "error"))
                    return
                
                self.ui.after(0, lambda: self.ui._update_site_theme(url_type))

                if url_type == "spotify":
                    track_name = self.spotify_downloader.get_track_name(url)
                    formats = self.spotify_downloader.get_available_formats()
                    self.ui.after(0, lambda: self.ui._update_spotify_ui(formats, track_name))
                elif url_type == "search":
                    self.ui.after(0, lambda: self.ui._update_status("🔍 Buscando mejores resultados...", "info"))
                    results = self.video_downloader.search_videos(url, count=5)
                    self.ui.after(0, lambda: self.ui.results_frame.display_results(results))
                    self.ui.after(0, lambda: self.ui.results_frame.pack(fill="x", pady=(0, 10), after=self.ui.url_frame))
                else:
                    playlist_info = self.video_downloader.get_playlist_info(url)
                    if playlist_info:
                        if playlist_info.get('is_playlist'):
                            self._playlist_info = playlist_info
                            self.ui.after(0, lambda: self.ui._show_playlist_options(playlist_info))
                            single_url = self.video_downloader.get_single_video_url(url)
                            if single_url:
                                self._download_url = single_url
                        else:
                            title = playlist_info.get('title', 'Video')
                            uploader = playlist_info.get('uploader', '')
                            duration = playlist_info.get('duration', 0)
                            # Get full info metadata for thumbnail if single video
                            video_meta = self.video_downloader.get_video_info(url, extract_flat=True)
                            thumb_url = video_meta.get('thumbnail') if video_meta else None
                            
                            self.ui.after(0, lambda t=title, u=uploader, d=duration, tb=thumb_url: self.ui._update_video_ui_simple(t, u, d, thumbnail_url=tb))
                    else:
                         self.ui.after(0, lambda: self.ui._update_video_ui_simple("Contenido detectado", "Listo para descargar"))

                self.ui.after(0, lambda: self.ui._update_status("Análisis completado", "success"))
                if PYGAME_LOADED and url_type in ["youtube", "spotify"] and self.ui.format_frame.download_type.get() == "audio":
                    self.ui.after(0, lambda: self.ui.player_frame.pack(fill="x", pady=(5, 0)))
            except Exception as e:
                self.ui.after(0, lambda: self.ui._update_status(f"Error: {str(e)}", "error"))
            finally:
                self._is_analyzing = False
                self.ui.after(0, lambda: self.ui.url_frame.set_analyzing(False))

        threading.Thread(target=analyze, daemon=True).start()

    def start_download(self):
        url = self.ui.url_frame.get_url()
        output_path = self.ui.format_frame.get_output_path()
        
        if not url:
            self.ui._update_status("Por favor ingresa una URL", "warning")
            return
        if not output_path or not os.path.isdir(output_path):
            self.ui._update_status("Por favor selecciona una carpeta válida", "warning")
            return
            
        self._set_downloading(True)
        self.ui.progress_bar.set(0)
        
        def download():
            try:
                self.ui.after(0, lambda: self.ui._update_status("📡 Conectando...", "info"))
                url_type = detect_url_type(url)
                quality = self.ui.format_frame.quality_combo.get()
                format_type = self.ui.format_frame.format_combo.get()
                download_type = self.ui.format_frame.download_type.get()
                
                actual_url = url
                if url_type == "search":
                    actual_url = self._download_url or f"ytsearch1:{url}"
                elif self._playlist_info and self._playlist_info.get('is_playlist'):
                    if self.ui.playlist_choice.get() == "single" and self._download_url:
                        actual_url = self._download_url
                
                # Pull trim range directly from the main UI frame controls
                active_trim = self.ui.format_frame.get_trim_range()
                
                if url_type == "spotify":
                    search_query = self.ui.spotify_search_entry.get().strip()
                    if not search_query:
                        self.ui.after(0, lambda: self.ui._update_status("Ingresa el nombre de la canción", "warning"))
                        self._set_downloading(False)
                        return
                    success, msg = self.spotify_downloader.download(url, output_path, format_type, quality, search_query)
                else:
                    download_as_playlist = False
                    if self._playlist_info and self._playlist_info.get('is_playlist'):
                        download_as_playlist = (self.ui.playlist_choice.get() == "playlist")
                    
                    if download_type == "video":
                        success = self.video_downloader.download_video(
                            actual_url, output_path, quality, format_type, download_as_playlist,
                            trim_range=active_trim
                        )
                    else:
                        success = self.video_downloader.download_audio(
                            actual_url, output_path, quality, format_type, download_as_playlist,
                            trim_range=active_trim
                        )
                
                # Reset trim range inside format_frame if finished
                self.ui.after(0, lambda: self.ui.format_frame.trim_var.set(False))
                self.ui.after(0, lambda: self.ui.format_frame._toggle_trim_inputs())
                self._trim_range = None
                
                if not success:
                    self.ui.after(0, lambda: self.ui._update_status("Error en la descarga", "error"))
            except Exception as e:
                self.ui.after(0, lambda: self.ui._update_status(f"Error: {str(e)}", "error"))
            finally:
                self._set_downloading(False)

        threading.Thread(target=download, daemon=True).start()

    def download_preview(self, override_url=None):
        url = override_url or self._download_url or self.ui.url_frame.get_url()
        if not url: return
        
        play_btn = self._active_widgets['play_btn'] if self._active_widgets else self.ui.player_frame.play_btn
        play_btn.configure(state="disabled", text="⌛")
        self.ui._update_status("⚡ Cargando avance rápido...", "info")
        
        def do_download():
            try:
                cache_dir = os.path.join(os.getcwd(), ".audio_cache")
                if not os.path.exists(cache_dir):
                    os.makedirs(cache_dir)
                
                url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
                out_file = os.path.join(cache_dir, f"pre_{url_hash}.mp3")
                
                if not os.path.exists(out_file):
                    ydl_opts = {
                        'format': 'bestaudio/best',
                        'outtmpl': out_file.replace('.mp3', '.%(ext)s'),
                        'quiet': True,
                        'no_warnings': True,
                        'external_downloader': 'ffmpeg',
                        'external_downloader_args': {'ffmpeg': ['-t', '30']},
                        'postprocessors': [{
                            'key': 'FFmpegExtractAudio',
                            'preferredcodec': 'mp3',
                            'preferredquality': '128',
                        }],
                    }
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([url])
                
                actual_file = out_file if os.path.exists(out_file) else None
                if not actual_file:
                    for f in os.listdir(cache_dir):
                        if f.startswith(f"pre_{url_hash}") and f.endswith(".mp3"):
                            actual_file = os.path.join(cache_dir, f)
                            break
                
                if actual_file:
                    self._preview_file = actual_file
                    self.ui.after(0, self.start_playback)
                else:
                    self.ui.after(0, lambda: self.ui._update_status("Error al cargar avance", "error"))
            except Exception as e:
                self.ui.after(0, lambda: self.ui._update_status(f"Error preview: {str(e)}", "error"))
            finally:
                self.ui.after(0, lambda: play_btn.configure(state="normal", text="▶"))

        threading.Thread(target=do_download, daemon=True).start()

    def start_playback(self):
        try:
            if PYGAME_LOADED:
                pygame.mixer.music.load(self._preview_file)
                pygame.mixer.music.play(start=self._playback_start_offset)
                self._preview_playing = True
                self._is_paused = False
                
                play_btn = self._active_widgets['play_btn'] if self._active_widgets else self.ui.player_frame.play_btn
                play_btn.configure(text="⏸")
                self.update_player_slider()
                self.ui._update_status("Listo para reproducir", "success")
        except Exception as e:
            self.ui._update_status(f"Error playback: {str(e)}", "error")

    def toggle_playback(self):
        if not self._preview_file:
            self.download_preview()
            return
            
        play_btn = self._active_widgets['play_btn'] if self._active_widgets else self.ui.player_frame.play_btn

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
            self.update_player_slider()

    def stop_preview(self):
        if PYGAME_LOADED:
            try:
                pygame.mixer.music.stop()
                pygame.mixer.music.unload()
            except: pass
        self._preview_playing = False
        self._is_paused = False
        self._preview_file = None
        self._playback_start_offset = 0
        
        play_btn = self._active_widgets['play_btn'] if self._active_widgets else (self.ui.player_frame.play_btn if hasattr(self.ui, 'player_frame') else None)
        slider = self._active_widgets['slider'] if self._active_widgets else (self.ui.player_frame.player_slider if hasattr(self.ui, 'player_frame') else None)
        
        if play_btn: play_btn.configure(text="▶")
        if slider: slider.set(0)

    def seek_audio(self, value):
        if self._preview_file and PYGAME_LOADED:
            duration = self._current_formats.get('duration', 0)
            if duration == 0: duration = 30
            
            pos = (float(value) / 100) * duration
            self._playback_start_offset = pos
            try:
                pygame.mixer.music.play(start=pos)
                if not self._preview_playing:
                    pygame.mixer.music.pause()
                else:
                    self.update_player_slider()
            except:
                pass

    def update_player_slider(self):
        if not self._preview_playing or not PYGAME_LOADED:
            return

        if not pygame.mixer.music.get_busy() and self._preview_playing:
            self._preview_playing = False
            play_btn = self._active_widgets['play_btn'] if self._active_widgets else self.ui.player_frame.play_btn
            play_btn.configure(text="▶")
            self._playback_start_offset = 0
            return

        current_ms = pygame.mixer.music.get_pos()
        if current_ms < 0: return
        
        current_sec = self._playback_start_offset + (current_ms / 1000.0)
        duration = self._current_formats.get('duration', 0)
        if duration == 0: duration = 30
        
        progress = (current_sec / duration) * 100
        
        slider = self._active_widgets['slider'] if self._active_widgets else self.ui.player_frame.player_slider
        time_label = self._active_widgets['time_label'] if self._active_widgets else self.ui.player_frame.time_label
        
        slider.set(progress)
        cur_min, cur_sec = int(current_sec) // 60, int(current_sec) % 60
        dur_min, dur_sec = int(duration) // 60, int(duration) % 60
        time_label.configure(text=f"{cur_min:02d}:{cur_sec:02d} / {dur_min:02d}:{dur_sec:02d}")
        
        if self._preview_playing:
            self.ui.after(500, self.update_player_slider)

    def preview_result(self, result, slider, time_label, play_btn):
        if self._download_url == result['url'] and self._preview_file:
            self.toggle_playback()
            return
        self.stop_preview()
        self._download_url = result['url']
        self._active_widgets = {
            'slider': slider,
            'time_label': time_label,
            'play_btn': play_btn
        }
        self._current_formats['duration'] = result['duration']
        self.download_preview(result['url'])

    def select_result(self, result):
        self.ui.url_frame.set_url(result['url'])
        self._last_analyzed_url = result['url']
        self._download_url = result['url']
        self._current_formats = {
            'title': result['title'],
            'uploader': result.get('uploader', 'Unknown'),
            'duration': result.get('duration', 0)
        }
        self.ui._update_video_ui_simple(
            result['title'], 
            result.get('uploader', 'Unknown'), 
            result.get('duration', 0),
            show_player=False,
            thumbnail_url=result.get('thumbnail')
        )

    def download_specific(self, result):
        try:
            self.ui._update_status("🔄 Seleccionando contenido...", "info")
            self.select_result(result)
            self.ui.update_idletasks()
            mode = self.ui.format_frame.download_type.get()
            self.ui._update_status(f"🚀 Iniciando {mode}: {result['title'][:30]}...", "success")
            self.ui.after(200, self.start_download)
        except Exception as e:
            self.ui._update_status(f"Error al iniciar: {str(e)}", "error")
