"""
Universal Downloader - Video/Audio Downloader Module
Uses yt-dlp to download from YouTube and 1000+ other sites.
"""

import os
import re
import yt_dlp
from typing import List, Dict, Optional, Callable, Any
from pathlib import Path


class VideoDownloader:
    """Handles video and audio downloads using yt-dlp."""
    
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
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': extract_flat,
            'noplaylist': False,  # Allow playlist detection
        }
        
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
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': 'in_playlist',  # Only get basic info
            'noplaylist': False,
        }
        
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
        # Extract video ID from YouTube URLs
        import re
        video_match = re.search(r'[?&]v=([a-zA-Z0-9_-]{11})', playlist_url)
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
            if fmt.get('vcodec') and fmt.get('vcodec') != 'none':
                height = fmt.get('height', 0)
                if height and height not in seen_video:
                    seen_video.add(height)
                    video_formats.append({
                        'format_id': format_id,
                        'quality': f"{height}p",
                        'height': height,
                        'ext': ext,
                        'fps': fmt.get('fps', 0),
                        'vcodec': fmt.get('vcodec', ''),
                        'filesize': fmt.get('filesize') or fmt.get('filesize_approx', 0),
                        'has_audio': fmt.get('acodec') and fmt.get('acodec') != 'none'
                    })
            
            # Audio-only formats
            elif fmt.get('acodec') and fmt.get('acodec') != 'none':
                abr = fmt.get('abr', 0)
                if abr and abr not in seen_audio:
                    seen_audio.add(abr)
                    audio_formats.append({
                        'format_id': format_id,
                        'quality': f"{int(abr)}kbps",
                        'abr': abr,
                        'ext': ext,
                        'acodec': fmt.get('acodec', ''),
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
        
        Args:
            url: Video URL
            output_path: Directory to save the file
            quality: Video quality (e.g., "1080p", "720p")
            format_ext: Output format (e.g., "mp4", "mkv")
            force_reencode: Force re-encoding to H.264/AAC for Discord compatibility
            download_playlist: If True, download the entire playlist if URL refers to one
            
        Returns:
            True if successful, False otherwise
        """
        # Parse quality to get height
        height_match = re.match(r'(\d+)p?', quality)
        height = int(height_match.group(1)) if height_match else 1080
        
        # Detect if URL is from TikTok (needs re-encoding for Discord)
        is_tiktok = 'tiktok.com' in url.lower() or 'vm.tiktok' in url.lower()
        needs_reencode = force_reencode or is_tiktok
        
        # Format string for best video + audio up to specified height
        format_string = f'bestvideo[height<={height}]+bestaudio/best[height<={height}]/best'
        
        ydl_opts = {
            'format': format_string,
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'merge_output_format': format_ext,
            'quiet': True,
            'no_warnings': True,
            'noplaylist': not download_playlist,
        }
        
        # Add re-encoding postprocessor for TikTok videos (Discord compatibility)
        if needs_reencode and format_ext == 'mp4':
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }]
            # Force H.264 video codec and AAC audio for maximum compatibility
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
        
        Args:
            url: Video/Audio URL
            output_path: Directory to save the file
            quality: Audio quality (e.g., "320kbps", "192kbps")
            format_ext: Output format (mp3, m4a, wav, etc.)
            download_playlist: If True, download the entire playlist if URL refers to one
            
        Returns:
            True if successful, False otherwise
        """
        # Parse quality to get bitrate
        quality_match = re.match(r'(\d+)', quality)
        bitrate = quality_match.group(1) if quality_match else "320"
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'progress_hooks': [self._progress_hook],
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': format_ext,
                'preferredquality': bitrate,
            }],
            'quiet': True,
            'no_warnings': True,
            'noplaylist': not download_playlist,
        }
        
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
    
    Args:
        url: The URL to analyze
        
    Returns:
        'spotify', 'youtube', 'other', or 'invalid'
    """
    url_lower = url.lower()
    
    if 'spotify.com' in url_lower or 'open.spotify' in url_lower:
        return 'spotify'
    elif 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif url.startswith('http://') or url.startswith('https://'):
        return 'other'  # Other supported sites
    else:
        return 'invalid'
