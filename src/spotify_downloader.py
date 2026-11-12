"""
Universal Downloader - Spotify/Search Downloader Module
Downloads music by searching on YouTube using yt-dlp.
For Spotify URLs, reads public embed metadata without an API key.
"""

import re
import requests
import yt_dlp
from typing import Optional, Callable, Dict, Tuple, List
from pathlib import Path
from src.config import config
from src.runtime import ydl_options
from src.urls import detect_url_type

# Pre-compiled regex patterns for better performance
SPOTIFY_URL_PATTERNS = [
    (re.compile(r'spotify\.com/(?:intl-[a-z]{2}/)?track/([a-zA-Z0-9]+)'), 'track'),
    (re.compile(r'spotify\.com/(?:intl-[a-z]{2}/)?album/([a-zA-Z0-9]+)'), 'album'),
    (re.compile(r'spotify\.com/(?:intl-[a-z]{2}/)?playlist/([a-zA-Z0-9]+)'), 'playlist'),
]
EMBED_NAME_REGEX = re.compile(r'"name":"([^"]+)"')
SAFE_FILENAME_REGEX = re.compile(r'[<>:"/\\|?*]')


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

    # Default yt-dlp options for searching and downloading
    YDL_SEARCH_OPTS = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'default_search': 'ytsearch1',
    }

    def __init__(self, progress_callback: Optional[Callable[[Dict], None]] = None):
        self.progress_callback = progress_callback
        self.last_downloaded_file: Optional[str] = None
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })

    def _get_base_opts(self) -> dict:
        return ydl_options(self.YDL_SEARCH_OPTS)

    def _extract_spotify_id(self, url: str) -> Optional[Tuple[str, str]]:
        """
        Extract track/album/playlist ID and type from Spotify URL.
        """
        if detect_url_type(url) != 'spotify':
            return None
        for pattern, content_type in SPOTIFY_URL_PATTERNS:
            match = pattern.search(url)
            if match:
                return content_type, match.group(1)
        return None

    def get_track_name(self, url: str) -> Optional[str]:
        """
        Get track/album name from Spotify URL using scraping.
        """
        extracted = self._extract_spotify_id(url)
        if not extracted:
            return None

        content_type, content_id = extracted

        # Rely exclusively on scraping embed page (no API needed)
        return self._scrape_embed_page(content_type, content_id)

    def _scrape_embed_page(self, content_type: str, content_id: str) -> Optional[str]:
        """
        Scrape Spotify embed page to get track name and artist.
        """
        embed_url = f"https://open.spotify.com/embed/{content_type}/{content_id}"

        try:
            response = self._session.get(embed_url, timeout=10)

            if response.ok:
                names = EMBED_NAME_REGEX.findall(response.text)

                if len(names) >= 2:
                    return f"{names[1]} - {names[0]}"
                elif len(names) == 1:
                    return names[0]
        except Exception as e:
            print(f"Embed scraping error: {e}")

        return None

    def _search_youtube(self, query: str) -> Optional[Dict]:
        """Search YouTube for a song and return the best match info."""
        try:
            enhanced_query = query
            if "audio" not in query.lower() and "oficial" not in query.lower():
                enhanced_query = f"{query} audio"

            search_query = f"ytsearch1:{enhanced_query}"
            ydl_opts = self._get_base_opts()

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
        """
        if format_type not in self.FORMATS:
            format_type = 'mp3'

        query = search_query or self.get_track_name(url)
        if not query:
            return False, "No se pudo obtener el nombre de la canción. Ingresa el nombre manualmente."

        try:
            if self.progress_callback:
                self.progress_callback({
                    'status': 'searching',
                    'message': f'Buscando: {query}',
                    'percent': 20
                })

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

            bitrate_num = re.sub(r'\D', '', bitrate) or '320'
            safe_title = SAFE_FILENAME_REGEX.sub('', video_title)

            ydl_opts = self._get_base_opts()
            ydl_opts.update({
                'outtmpl': str(Path(output_path) / f'{safe_title}.%(ext)s'),
                'progress_hooks': [self._progress_hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_type,
                    'preferredquality': bitrate_num,
                }],
            })

            self.last_downloaded_file = None
            def _post_hook(filepath):
                self.last_downloaded_file = filepath

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.add_post_hook(_post_hook)
                result = ydl.download([video_url])
            if result != 0 or not self.last_downloaded_file:
                return False, "No se generó un archivo de audio final."

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
    return detect_url_type(url) == 'spotify'
