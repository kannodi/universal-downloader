"""
Universal Downloader - Video/Audio Downloader Module
Uses yt-dlp to download from YouTube and 1000+ other sites.
"""

import os
import re
import yt_dlp
from typing import List, Dict, Optional, Callable, Any
from pathlib import Path

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
    }
    
    def __init__(self, progress_callback: Optional[Callable[[Dict], None]] = None):
        """
        Initialize the downloader.
        
        Args:
            progress_callback: Function to call with progress updates
        """
        self.progress_callback = progress_callback
        self._current_info = None
    
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
        ydl_opts = self.DEFAULT_YDL_OPTS.copy()
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
        ydl_opts = self.DEFAULT_YDL_OPTS.copy()
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
        Extract single video URL from a playlist URL if it contains a video ID.
        
        Args:
            playlist_url: URL that may contain both playlist and video ID
            
        Returns:
            Single video URL or None
        """
        video_match = YOUTUBE_VIDEO_ID_REGEX.search(playlist_url)
        if video_match:
            return f"https://www.youtube.com/watch?v={video_match.group(1)}"
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
    
    def download_video(
        self,
        url: str,
        output_path: str,
        quality: str = "1080p",
        format_ext: str = "mp4",
        force_reencode: bool = False,
        download_playlist: bool = False
    ) -> bool:
        """
        Download video in specified quality.
        """
        # Parse quality to get height
        height_match = QUALITY_HEIGHT_REGEX.match(quality)
        height = int(height_match.group(1)) if height_match else 1080
        
        is_tiktok = 'tiktok.com' in url.lower() or 'vm.tiktok' in url.lower()
        needs_reencode = force_reencode or is_tiktok
        
        format_string = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
        
        ydl_opts = self.DEFAULT_YDL_OPTS.copy()
        ydl_opts.update({
            'format': format_string,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'merge_output_format': format_ext,
            'noplaylist': not download_playlist,
        })
        
        # Add re-encoding postprocessor for compatibility
        if needs_reencode and format_ext == 'mp4':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
            ydl_opts['postprocessor_args'] = {
                'FFmpegVideoConvertor': ['-c:v', 'libx264', '-c:a', 'aac', '-movflags', '+faststart']
            }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
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
        download_playlist: bool = False
    ) -> bool:
        """
        Download audio only in specified quality.
        """
        quality_match = BITRATE_REGEX.match(quality)
        bitrate = quality_match.group(1) if quality_match else "320"
        
        ydl_opts = self.DEFAULT_YDL_OPTS.copy()
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
        })
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            return True
        except Exception as e:
            if self.progress_callback:
                self.progress_callback({'status': 'error', 'error': str(e)})
            return False


def detect_url_type(url: str) -> str:
    """
    Detect the type of URL.
    """
    url_lower = url.lower()
    
    if 'spotify.com' in url_lower or 'open.spotify' in url_lower:
        return 'spotify'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif url.startswith('http://') or url.startswith('https://'):
        return 'other'
    else:
        return 'invalid'
