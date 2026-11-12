"""
Universal Downloader - Video/Audio Downloader Module
Uses yt-dlp to download from YouTube and 1000+ other sites.
"""

import os
import sys
import re
import shutil
import subprocess
import yt_dlp
from typing import List, Dict, Optional, Callable, Any, Tuple
from pathlib import Path
from src.config import config
from src.runtime import binary_path, ydl_options
from src.urls import detect_url_type

def _get_binary_cmd(binary_name: str, custom_location: Optional[str] = None) -> str:
    """Find binary executable (e.g. ffmpeg, ffprobe) in custom_location, local bin, or PATH."""
    return binary_path(binary_name, custom_location)

def _probe_media(filepath: str, ffmpeg_location: Optional[str] = None) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Returns (video_codec, pixel_format, audio_codec) using ffprobe."""
    ffprobe_cmd = _get_binary_cmd("ffprobe", ffmpeg_location)
    creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
    vcodec, pix_fmt, acodec = None, None, None
    try:
        res_v = subprocess.run([
            ffprobe_cmd, "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=codec_name,pix_fmt",
            "-of", "csv=p=0",
            filepath
        ], capture_output=True, text=True, creationflags=creationflags)
        if res_v.returncode == 0 and res_v.stdout.strip():
            parts = res_v.stdout.strip().split(',')
            vcodec = parts[0].strip().lower() if len(parts) > 0 else None
            pix_fmt = parts[1].strip().lower() if len(parts) > 1 else None

        res_a = subprocess.run([
            ffprobe_cmd, "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=codec_name",
            "-of", "csv=p=0",
            filepath
        ], capture_output=True, text=True, creationflags=creationflags)
        if res_a.returncode == 0 and res_a.stdout.strip():
            acodec = res_a.stdout.strip().lower()
    except Exception as e:
        print(f"Error probing media with ffprobe: {e}")
    return vcodec, pix_fmt, acodec

def _has_faststart(filepath: str) -> bool:
    """Checks whether the 'moov' atom comes before 'mdat' in an MP4 file."""
    try:
        with open(filepath, 'rb') as f:
            while True:
                header = f.read(8)
                if len(header) < 8:
                    break
                size = int.from_bytes(header[:4], 'big')
                tag = header[4:8]
                if tag == b'moov':
                    return True
                if tag == b'mdat':
                    return False
                if size == 1:
                    large_size = f.read(8)
                    if len(large_size) < 8:
                        break
                    size = int.from_bytes(large_size, 'big')
                    f.seek(size - 16, os.SEEK_CUR)
                elif size > 8:
                    f.seek(size - 8, os.SEEK_CUR)
                else:
                    break
    except Exception:
        pass
    return False

class EnsureMP4CompatibilityPP(yt_dlp.postprocessor.PostProcessor):
    """
    Ensures that MP4 files are fully compatible with Discord, web browsers, and mobile players:
    - Video codec: H.264 (yuv420p)
    - Audio codec: AAC (or stripped if no_audio=True)
    - Faststart: moov atom at the beginning of the file for instant playback/streaming
    """
    def __init__(self, downloader=None, ffmpeg_location=None, no_audio=False):
        super().__init__(downloader)
        self.ffmpeg_location = ffmpeg_location
        self.no_audio = no_audio

    def run(self, info):
        filepath = info.get('filepath') or info.get('_filename')
        if not filepath or not os.path.exists(filepath):
            return [], info

        if not filepath.lower().endswith('.mp4'):
            return [], info

        vcodec, pix_fmt, acodec = _probe_media(filepath, self.ffmpeg_location)

        # Video check: must be H.264 (avc1/h264) and yuv420p (8-bit)
        needs_video_transcode = False
        if vcodec:
            is_h264 = any(vcodec.startswith(c) for c in ['h264', 'avc'])
            is_yuv420p = (pix_fmt == 'yuv420p') if pix_fmt else True
            if not is_h264 or not is_yuv420p:
                needs_video_transcode = True
        else:
            vcodec_info = (info.get('vcodec') or '').lower()
            if vcodec_info and not any(vcodec_info.startswith(c) for c in ['h264', 'avc']):
                needs_video_transcode = True

        # Audio check: if no_audio, remove audio; else ensure compatible AAC/MP3
        needs_audio_strip = self.no_audio and (acodec is not None)
        needs_audio_transcode = False
        if not self.no_audio and acodec:
            if not any(acodec.startswith(a) for a in ['aac', 'mp4a', 'mp3']):
                needs_audio_transcode = True

        has_faststart = _has_faststart(filepath)

        # Skip if already 100% compliant
        if not needs_video_transcode and not needs_audio_strip and not needs_audio_transcode and has_faststart:
            return [], info

        ffmpeg_cmd = _get_binary_cmd("ffmpeg", self.ffmpeg_location)
        temp_file = filepath + ".compat.mp4"
        cmd = [ffmpeg_cmd, "-y", "-i", filepath]

        if needs_video_transcode:
            cmd.extend(["-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p"])
        else:
            cmd.extend(["-c:v", "copy"])

        if self.no_audio:
            cmd.append("-an")
        elif needs_audio_transcode:
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        else:
            cmd.extend(["-c:a", "copy"])

        cmd.extend(["-movflags", "+faststart", temp_file])

        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
            subprocess.run(cmd, creationflags=creationflags, check=True)
            if os.path.exists(temp_file):
                os.replace(temp_file, filepath)
        except Exception as e:
            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except OSError:
                    pass
            raise yt_dlp.utils.PostProcessingError(f"Error ensuring MP4 compatibility: {e}") from e

        return [], info

class StripAudioPP(yt_dlp.postprocessor.PostProcessor):
    def __init__(self, downloader=None, ffmpeg_location=None):
        super().__init__(downloader)
        self.ffmpeg_location = ffmpeg_location

    def run(self, info):
        filepath = info.get('filepath') or info.get('_filename')
        if filepath and os.path.exists(filepath):
            ffmpeg_cmd = _get_binary_cmd("ffmpeg", self.ffmpeg_location)
            temp_file = filepath + ".tmp" + os.path.splitext(filepath)[1]
            try:
                creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0
                subprocess.run([
                    ffmpeg_cmd, "-y", "-i", filepath,
                    "-c:v", "copy", "-an", temp_file
                ], creationflags=creationflags, check=True)
                os.replace(temp_file, filepath)
            except Exception as e:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                raise yt_dlp.utils.PostProcessingError(f"Error stripping audio: {e}") from e
        return [], info

# Pre-compiled regex patterns for better performance
YOUTUBE_VIDEO_ID_REGEX = re.compile(r'[?&]v=([a-zA-Z0-9_-]{11})')
QUALITY_HEIGHT_REGEX = re.compile(r'(\d+)p?')
BITRATE_REGEX = re.compile(r'(\d+)')


class VideoDownloader:
    """Handles video and audio downloads using yt-dlp."""

    # Default yt-dlp options
    DEFAULT_YDL_OPTS = {
        'quiet': True,
        'no_warnings': True,
        'noplaylist': False,
        'socket_timeout': 5,
        'ignoreerrors': False,
    }

    def __init__(self, progress_callback: Optional[Callable[[Dict], None]] = None):
        """
        Initialize the downloader.

        Args:
            progress_callback: Function to call with progress updates
        """
        self.progress_callback = progress_callback
        self._current_info = None
        self.last_downloaded_file: Optional[str] = None
        self.downloaded_files: List[str] = []

    def _post_hook(self, filepath: str) -> None:
        """Called by yt-dlp after all post-processing on the final file is complete."""
        self.last_downloaded_file = filepath
        self.downloaded_files.append(filepath)

    def _get_base_opts(self) -> dict:
        return ydl_options(self.DEFAULT_YDL_OPTS)

    def _progress_hook(self, d: Dict) -> None:
        """Internal progress hook for yt-dlp."""
        if self.progress_callback:
            status = d.get('status', '')

            if status == 'downloading':
                progress = {
                    'status': 'downloading',
                    'downloaded_bytes': d.get('downloaded_bytes', 0),
                    'total_bytes': d.get('total_bytes') or d.get('total_bytes_estimate', 0),
                    'speed': d.get('speed', 0),
                    'eta': d.get('eta', 0),
                    'filename': d.get('filename', ''),
                    'percent': 0
                }
                if progress['total_bytes'] > 0:
                    progress['percent'] = (progress['downloaded_bytes'] / progress['total_bytes']) * 100
                self.progress_callback(progress)

            elif status == 'finished':
                self.progress_callback({
                    'status': 'finished',
                    'filename': d.get('filename', ''),
                    'percent': 100
                })

            elif status == 'error':
                self.progress_callback({
                    'status': 'error',
                    'error': d.get('error', 'Unknown error')
                })

    def get_video_info(self, url: str, extract_flat: bool = False) -> Optional[Dict]:
        """
        Get video information without downloading.

        Args:
            url: Video URL
            extract_flat: If True, don't extract full info for playlists (faster)

        Returns:
            Dictionary with video information or None if error
        """
        ydl_opts = self._get_base_opts()
        ydl_opts['extract_flat'] = extract_flat

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                self._current_info = info
                return info
        except Exception as e:
            print(f"Error getting video info: {e}")
            return None

    def get_playlist_info(self, url: str) -> Optional[Dict]:
        """
        Get playlist information quickly without extracting all videos.

        Args:
            url: Playlist URL

        Returns:
            Dictionary with playlist info or None if not a playlist
        """
        ydl_opts = self._get_base_opts()
        ydl_opts['extract_flat'] = 'in_playlist'

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

                # Check if it's a playlist
                if info.get('_type') == 'playlist' or 'entries' in info:
                    entries = list(info.get('entries', []))
                    return {
                        'is_playlist': True,
                        'title': info.get('title', 'Playlist'),
                        'uploader': info.get('uploader', 'Unknown'),
                        'count': len(entries),
                        'entries': entries[:10],  # Only first 10 for preview
                        'url': url
                    }
                else:
                    # Single video
                    return {
                        'is_playlist': False,
                        'title': info.get('title', 'Unknown'),
                        'uploader': info.get('uploader', 'Unknown'),
                        'duration': info.get('duration', 0),
                        'url': url
                    }
        except Exception as e:
            print(f"Error getting playlist info: {e}")
            return None

    def get_single_video_url(self, playlist_url: str) -> Optional[str]:
        """
        Extract single video URL from a playlist URL if it contains a video ID,
        otherwise fallback to extracting the URL of the first video in the playlist.

        Args:
            playlist_url: URL of the video/playlist

        Returns:
            Single video URL or None
        """
        video_match = YOUTUBE_VIDEO_ID_REGEX.search(playlist_url)
        if video_match:
            return f"https://www.youtube.com/watch?v={video_match.group(1)}"

        # Fallback: Extract the first video's URL from the playlist metadata
        try:
            ydl_opts = self._get_base_opts()
            ydl_opts['extract_flat'] = True
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(playlist_url, download=False)
                if info and 'entries' in info:
                    entries = list(info.get('entries', []))
                    if entries and entries[0]:
                        first_entry = entries[0]
                        # Some extractors return 'url' directly, others return 'id'
                        video_id = first_entry.get('id') or first_entry.get('url')
                        if video_id:
                            if video_id.startswith('http'):
                                return video_id
                            return f"https://www.youtube.com/watch?v={video_id}"
        except Exception as e:
            print(f"Error falling back to first playlist video: {e}")
        return None

    def get_available_formats(self, url: str) -> Dict[str, List[Dict]]:
        """
        Get available video and audio formats for a URL.

        Args:
            url: Video URL

        Returns:
            Dictionary with 'video' and 'audio' format lists
        """
        info = self.get_video_info(url)
        if not info:
            return {'video': [], 'audio': [], 'title': '', 'thumbnail': ''}

        formats = info.get('formats', [])

        video_formats = []
        audio_formats = []
        seen_video = set()
        seen_audio = set()

        for fmt in formats:
            format_id = fmt.get('format_id', '')
            ext = fmt.get('ext', '')

            # Video formats
            vcodec = fmt.get('vcodec')
            if vcodec and vcodec != 'none':
                height = fmt.get('height', 0)
                if height and height not in seen_video:
                    seen_video.add(height)
                    video_formats.append({
                        'format_id': format_id,
                        'quality': f"{height}p",
                        'height': height,
                        'ext': ext,
                        'fps': fmt.get('fps', 0),
                        'vcodec': vcodec,
                        'filesize': fmt.get('filesize') or fmt.get('filesize_approx', 0),
                        'has_audio': fmt.get('acodec') and fmt.get('acodec') != 'none'
                    })

            # Audio-only formats
            acodec = fmt.get('acodec')
            if acodec and acodec != 'none':
                abr = fmt.get('abr', 0)
                if abr and abr not in seen_audio:
                    seen_audio.add(abr)
                    audio_formats.append({
                        'format_id': format_id,
                        'quality': f"{int(abr)}kbps",
                        'abr': abr,
                        'ext': ext,
                        'acodec': acodec,
                        'filesize': fmt.get('filesize') or fmt.get('filesize_approx', 0)
                    })

        # Sort by quality (highest first)
        video_formats.sort(key=lambda x: x['height'], reverse=True)
        audio_formats.sort(key=lambda x: x['abr'], reverse=True)

        return {
            'video': video_formats,
            'audio': audio_formats,
            'title': info.get('title', 'Unknown'),
            'thumbnail': info.get('thumbnail', ''),
            'duration': info.get('duration', 0),
            'uploader': info.get('uploader', 'Unknown')
        }

    def download_video(self, url: str, output_path: str, quality: str = "1080p",
                     format_type: str = "mp4", is_playlist: bool = False, trim_range: Optional[Dict] = None, no_audio: bool = False) -> bool:
        """Download a single video or full playlist."""
        # Parse quality to get height
        height_match = QUALITY_HEIGHT_REGEX.match(quality)
        height = int(height_match.group(1)) if height_match else 1080

        if no_audio:
            # Only request bestvideo (mute)
            format_string = f'bestvideo[height<={height}]/bestvideo/best'
        else:
            format_string = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'

        ydl_opts = self._get_base_opts()
        ydl_opts.update({
            'format': format_string,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'merge_output_format': format_type,
            'noplaylist': not is_playlist,
            'match_filter': self._duration_filter,
        })

        if format_type == "mp4":
            ydl_opts['format_sort'] = ['vcodec:h264', 'res', 'acodec:m4a']
            ydl_opts['postprocessor_args'] = {
                'Merger': ['-movflags', '+faststart'],
                'FFmpegVideoRemuxer': ['-movflags', '+faststart'],
            }

        if trim_range:
            def parse_time(time_str):
                try:
                    parts = time_str.split(':')
                    if len(parts) == 2:
                        return int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    return int(time_str)
                except:
                    return 0
            start_sec = parse_time(trim_range.get("start", "0:00"))
            end_sec = parse_time(trim_range.get("end", "0:00"))
            if end_sec > start_sec:
                # Direct callback syntax according to modern yt-dlp version specification
                ydl_opts['download_ranges'] = lambda info_dict, self_ydl=None: [{
                    'start_time': start_sec,
                    'end_time': end_sec,
                    'title': info_dict.get('title', 'video') if info_dict else 'video'
                }]
                ydl_opts['force_keyframes_at_cuts'] = True

        self.last_downloaded_file = None
        self.downloaded_files = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.add_post_hook(self._post_hook)
                local_ffmpeg = ydl_opts.get('ffmpeg_location')
                if format_type == "mp4":
                    ydl.add_post_processor(EnsureMP4CompatibilityPP(ydl, local_ffmpeg, no_audio=no_audio))
                elif no_audio:
                    ydl.add_post_processor(StripAudioPP(ydl, local_ffmpeg))
                result = ydl.download([url])
            return result == 0 and bool(self.downloaded_files)
        except Exception as e:
            if self.progress_callback:
                self.progress_callback({'status': 'error', 'error': str(e)})
            return False

    def download_audio(
        self,
        url: str,
        output_path: str,
        quality: str = "320kbps",
        format_ext: str = "mp3",
        download_playlist: bool = False,
        trim_range: Optional[Dict] = None
    ) -> bool:
        """
        Download audio only in specified quality.
        """
        quality_match = BITRATE_REGEX.match(quality)
        bitrate = quality_match.group(1) if quality_match else "320"

        ydl_opts = self._get_base_opts()
        ydl_opts.update({
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format_ext,
                'preferredquality': bitrate,
            }],
            'noplaylist': not download_playlist,
            'match_filter': self._duration_filter,
        })

        if trim_range:
            def parse_time(time_str):
                try:
                    parts = time_str.split(':')
                    if len(parts) == 2:
                        return int(parts[0]) * 60 + int(parts[1])
                    elif len(parts) == 3:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
                    return int(time_str)
                except:
                    return 0
            start_sec = parse_time(trim_range.get("start", "0:00"))
            end_sec = parse_time(trim_range.get("end", "0:00"))
            if end_sec > start_sec:
                ydl_opts['download_ranges'] = lambda info_dict, self_ydl=None: [{
                    'start_time': start_sec,
                    'end_time': end_sec,
                    'title': info_dict.get('title', 'audio') if info_dict else 'audio'
                }]
                ydl_opts['force_keyframes_at_cuts'] = True

        self.last_downloaded_file = None
        self.downloaded_files = []

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.add_post_hook(self._post_hook)
                result = ydl.download([url])
            return result == 0 and bool(self.downloaded_files)
        except Exception as e:
            if self.progress_callback:
                self.progress_callback({'status': 'error', 'error': str(e)})
            return False

    def search_videos(self, query: str, count: int = 5) -> List[Dict]:
        """Search for videos based on a query."""
        ydl_opts = self._get_base_opts()
        ydl_opts['extract_flat'] = True
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(f"ytsearch{count}:{query}", download=False)
                if 'entries' in info:
                    return [{
                        'id': e.get('id'),
                        'url': f"https://www.youtube.com/watch?v={e.get('id')}",
                        'title': e.get('title'),
                        'uploader': e.get('uploader'),
                        'duration': e.get('duration', 0),
                        'thumbnail': e.get('thumbnail')
                    } for e in info['entries']]
                return []
        except Exception as e:
            print(f"Error searching videos: {e}")
            return []

    def _duration_filter(self, info_dict, *, incomplete):
        """Skip videos longer than 30 minutes (1800 seconds)."""
        duration = info_dict.get('duration')
        if duration and duration > 1800:
            return 'El video es demasiado largo (máximo 30 minutos)'
        return None
