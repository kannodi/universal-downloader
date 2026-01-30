"""
Universal Downloader - Spotify/Search Downloader Module
Downloads music by searching on YouTube using yt-dlp.
For Spotify URLs, extracts track info using Spotify Web API.
"""

import re
import yt_dlp
from typing import Optional, Callable, Dict, Tuple, List
from pathlib import Path


class SpotifyDownloader:
    """Downloads music by searching YouTube with track info from Spotify."""
    
    # Available formats and qualities
    FORMATS = ['mp3', 'm4a', 'flac', 'wav', 'ogg', 'opus']
    QUALITIES = {
        'mp3': ['320kbps', '256kbps', '192kbps', '128kbps'],
        'm4a': ['256kbps', '192kbps', '128kbps'],
        'flac': ['Lossless'],
        'wav': ['Lossless'],
        'ogg': ['320kbps', '256kbps', '192kbps', '128kbps'],
        'opus': ['256kbps', '192kbps', '128kbps']
    }
    
    def __init__(self, progress_callback: Optional[Callable[[Dict], None]] = None):
        self.progress_callback = progress_callback
        self._spotify = None
        self._init_spotify()
    
    def _init_spotify(self):
        """Initialize Spotify client if credentials available."""
        try:
            from .config import config
            client_id, client_secret = config.get_spotify_credentials()
            
            if client_id and client_secret:
                import spotipy
                from spotipy.oauth2 import SpotifyClientCredentials
                
                auth_manager = SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret
                )
                self._spotify = spotipy.Spotify(auth_manager=auth_manager)
                print("Spotify client initialized successfully")
        except ImportError as e:
            print(f"spotipy not installed: {e}")
            self._spotify = None
        except Exception as e:
            print(f"Could not init Spotify client: {e}")
            self._spotify = None
    
    def reinit_spotify(self):
        """Reinitialize Spotify client (call after credentials change)."""
        self._spotify = None
        self._init_spotify()
    
    def _extract_spotify_id(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Extract track/album/playlist ID and type from Spotify URL.
        Handles URLs with intl-XX prefix (e.g., intl-es/track/XXX)
        Returns (type, id) tuple or None.
        """
        # Updated patterns to handle optional intl-XX/ prefix
        patterns = [
            r'spotify\.com/(?:intl-[a-z]{2}/)?track/([a-zA-Z0-9]+)',
            r'spotify\.com/(?:intl-[a-z]{2}/)?album/([a-zA-Z0-9]+)',
            r'spotify\.com/(?:intl-[a-z]{2}/)?playlist/([a-zA-Z0-9]+)',
        ]
        types = ['track', 'album', 'playlist']
        
        for pattern, content_type in zip(patterns, types):
            match = re.search(pattern, url)
            if match:
                return content_type, match.group(1)
        return None
    
    def get_track_name(self, url: str) -> Optional[str]:
        """
        Get track/album name from Spotify URL.
        Uses embed page scraping (no API needed), falls back to spotipy if configured.
        """
        extracted = self._extract_spotify_id(url)
        if not extracted:
            return None
        
        content_type, content_id = extracted
        
        # Method 1: Scrape embed page (no API needed)
        track_name = self._scrape_embed_page(content_type, content_id)
        if track_name:
            return track_name
        
        # Method 2: Use spotipy API if configured
        if self._spotify:
            try:
                if content_type == 'track':
                    track = self._spotify.track(content_id)
                    artists = ', '.join([a['name'] for a in track['artists']])
                    return f"{artists} - {track['name']}"
                elif content_type == 'album':
                    album = self._spotify.album(content_id)
                    artists = ', '.join([a['name'] for a in album['artists']])
                    return f"{artists} - {album['name']}"
                elif content_type == 'playlist':
                    playlist = self._spotify.playlist(content_id, fields='name,owner.display_name')
                    return f"{playlist['name']} by {playlist['owner']['display_name']}"
            except Exception as e:
                print(f"Spotipy error: {e}")
        
        return None
    
    def _scrape_embed_page(self, content_type: str, content_id: str) -> Optional[str]:
        """
        Scrape Spotify embed page to get track name and artist.
        This works without API credentials.
        """
        import requests
        
        embed_url = f"https://open.spotify.com/embed/{content_type}/{content_id}"
        
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            
            response = requests.get(embed_url, headers=headers, timeout=10)
            
            if response.ok:
                # Extract "name" values from JSON in page
                # Pattern matches: "name":"SongTitle" and "name":"ArtistName"
                names = re.findall(r'"name":"([^"]+)"', response.text)
                
                if len(names) >= 2:
                    # Usually first is song title, second is artist
                    song_title = names[0]
                    artist_name = names[1]
                    return f"{artist_name} - {song_title}"
                elif len(names) == 1:
                    return names[0]
        except Exception as e:
            print(f"Embed scraping error: {e}")
        
        return None
    
    def _search_youtube(self, query: str) -> Optional[Dict]:
        """Search YouTube for a song and return the best match info."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'default_search': 'ytsearch1',
        }
        
        try:
            search_query = f"ytsearch1:{query}"
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(search_query, download=False)
                
                if info and 'entries' in info and info['entries']:
                    return info['entries'][0]
                elif info and info.get('id'):
                    return info
        except Exception as e:
            print(f"Error searching YouTube: {e}")
        return None
    
    def get_available_formats(self) -> Dict[str, list]:
        """Get available download formats and qualities."""
        return {
            'formats': self.FORMATS,
            'qualities': self.QUALITIES
        }
    
    def download(
        self,
        url: str,
        output_path: str,
        format_type: str = "mp3",
        bitrate: str = "320kbps",
        search_query: str = None
    ) -> Tuple[bool, str]:
        """
        Download music by searching YouTube.
        
        Args:
            url: Original Spotify URL (for reference)
            output_path: Directory to save files
            format_type: Output format
            bitrate: Audio bitrate
            search_query: Song/artist to search for (optional if URL has track info)
            
        Returns:
            Tuple of (success, message)
        """
        if format_type not in self.FORMATS:
            format_type = 'mp3'
        
        # Use provided query or try to get from URL
        query = search_query
        if not query:
            query = self.get_track_name(url)
        
        if not query:
            return False, "No se pudo obtener el nombre de la canción. Ingresa el nombre manualmente."
        
        try:
            if self.progress_callback:
                self.progress_callback({
                    'status': 'searching',
                    'message': f'Buscando: {query}',
                    'percent': 20
                })
            
            # Search on YouTube
            video_info = self._search_youtube(query)
            
            if not video_info:
                return False, f"No se encontró '{query}' en YouTube"
            
            video_url = f"https://www.youtube.com/watch?v={video_info.get('id')}"
            video_title = video_info.get('title', query)
            
            if self.progress_callback:
                self.progress_callback({
                    'status': 'downloading',
                    'message': f'Descargando: {video_title}',
                    'percent': 40
                })
            
            # Download using yt-dlp
            bitrate_num = re.sub(r'\D', '', bitrate) or '320'
            
            # Clean filename
            safe_title = re.sub(r'[<>:"/\\|?*]', '', video_title)
            
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': str(Path(output_path) / f'{safe_title}.%(ext)s'),
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type,
                    'preferredquality': bitrate_num,
                }],
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [self._progress_hook],
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])
            
            if self.progress_callback:
                self.progress_callback({
                    'status': 'finished',
                    'message': f'✅ Descargado: {video_title}',
                    'percent': 100
                })
            
            return True, f"Descargado: {video_title}"
            
        except Exception as e:
            error_msg = f"Error: {str(e)}"
            if self.progress_callback:
                self.progress_callback({
                    'status': 'error',
                    'message': error_msg
                })
            return False, error_msg
    
    def _progress_hook(self, d):
        """Handle yt-dlp progress updates."""
        if not self.progress_callback:
            return
        
        if d['status'] == 'downloading':
            percent = 40
            if 'downloaded_bytes' in d and 'total_bytes' in d and d['total_bytes'] > 0:
                percent = 40 + int(50 * d['downloaded_bytes'] / d['total_bytes'])
            
            self.progress_callback({
                'status': 'downloading',
                'message': 'Descargando audio...',
                'percent': min(percent, 90)
            })
        elif d['status'] == 'finished':
            self.progress_callback({
                'status': 'converting',
                'message': 'Convirtiendo audio...',
                'percent': 95
            })


def is_spotify_url(url: str) -> bool:
    """Check if a URL is a Spotify URL."""
    return 'spotify.com' in url.lower() or 'open.spotify' in url.lower()
