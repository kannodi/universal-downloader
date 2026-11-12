"""Offline regression tests. Run with python -m unittest discover -s tests -v."""

import json
import io
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest.mock import MagicMock, patch

from src.config import Config, DEFAULTS
from src.runtime import binary_path, ydl_options
from src.urls import detect_url_type
from src.spotify_downloader import SpotifyDownloader, is_spotify_url
from src.video_downloader import VideoDownloader, StripAudioPP
from src.gui.controller import DownloadController
from src.dependency_checker import install_ffmpeg
import yt_dlp


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def test_invalid_json_and_non_object_use_defaults(self):
        for text in ('{broken', '[]', 'null', '42'):
            with self.subTest(text=text):
                (self.directory / 'config.json').write_text(text, encoding='utf-8')
                self.assertEqual(Config(self.directory).get('theme'), DEFAULTS['theme'])

    def test_partial_preferences_merge_and_round_trip(self):
        (self.directory / 'config.json').write_text('{"theme": "light"}', encoding='utf-8')
        config = Config(self.directory)
        self.assertEqual(config.get('theme'), 'light')
        self.assertEqual(config.get('default_video_format'), 'mp4')
        config.set('last_download_path', 'Música')
        self.assertEqual(Config(self.directory).get('last_download_path'), 'Música')

    def test_failed_replace_preserves_previous_file_and_cleans_temp(self):
        config = Config(self.directory)
        config.set('theme', 'light')
        with patch('src.config.os.replace', side_effect=OSError('locked')):
            with self.assertRaises(OSError):
                config.set('theme', 'dark')
        self.assertEqual(json.loads(config.config_file.read_text())['theme'], 'light')
        self.assertEqual(list(self.directory.iterdir()), [config.config_file])


class UrlTests(unittest.TestCase):
    def test_input_types_and_hostname_boundaries(self):
        cases = {
            '': 'invalid', '  ': 'invalid', 'song title': 'search',
            ' https://youtu.be/123 ': 'youtube',
            'https://music.youtube.com/watch?v=123': 'youtube',
            'HTTPS://OPEN.SPOTIFY.COM/track/123': 'spotify',
            'https://spotify.com.attacker.test/track/123': 'other',
            'https://example.org/?q=youtube.com': 'other',
            'https://youtube.com@example.org/': 'other',
            'https://': 'invalid', 'https://[invalid': 'invalid',
            'ftp://example.org/file': 'invalid',
        }
        for value, expected in cases.items():
            with self.subTest(value=value):
                self.assertEqual(detect_url_type(value), expected)
        self.assertFalse(is_spotify_url('https://example.org/spotify.com/track/abc'))


class RuntimeTests(unittest.TestCase):
    def test_local_binary_does_not_depend_on_working_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
            (Path(directory) / executable).touch()
            with patch('src.runtime.BIN_DIR', Path(directory)):
                self.assertEqual(binary_path('ffmpeg'), str(Path(directory) / executable))
                self.assertEqual(ydl_options()['ffmpeg_location'], directory)

    def test_shared_cookie_options_and_no_mutation(self):
        original = {'quiet': False}
        with patch('src.runtime.config.get', return_value='firefox'):
            options = ydl_options(original)
        self.assertEqual(options['cookiesfrombrowser'], ('firefox',))
        self.assertEqual(original, {'quiet': False})
        self.assertNotIn('nocheckcertificate', options)

    def test_ffmpeg_installer_validates_archive_and_extracts_only_binaries(self):
        for names, expected in ((['ffmpeg.exe'], False), (['ffmpeg.exe', 'ffprobe.exe'], True)):
            archive = io.BytesIO()
            with zipfile.ZipFile(archive, 'w') as output:
                for name in names:
                    output.writestr(f'release/bin/{name}', b'binary')
                output.writestr('../unwanted.txt', b'ignored')
            with self.subTest(names=names), tempfile.TemporaryDirectory() as directory, \
                 patch('src.dependency_checker.sys.platform', 'win32'), \
                 patch('src.dependency_checker.BIN_DIR', Path(directory)), \
                 patch('urllib.request.urlopen', return_value=io.BytesIO(archive.getvalue())):
                success, message = install_ffmpeg()
                self.assertEqual(success, expected, message)
                self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), sorted(names) if expected else [])


class DownloadTests(unittest.TestCase):
    def test_error_result_and_empty_success_are_failures(self):
        for result in (1, 0):
            with self.subTest(result=result), patch('src.video_downloader.yt_dlp.YoutubeDL') as factory:
                factory.return_value.__enter__.return_value.download.return_value = result
                downloader = VideoDownloader()
                self.assertFalse(downloader.download_video('https://example.org', '.'))
                self.assertFalse(downloader.download_audio('https://example.org', '.'))

    def test_success_requires_final_post_hook(self):
        with patch('src.video_downloader.yt_dlp.YoutubeDL') as factory:
            ydl = factory.return_value.__enter__.return_value
            ydl.download.side_effect = lambda urls: (ydl.add_post_hook.call_args.args[0]('final.mp3'), 0)[1]
            downloader = VideoDownloader()
            self.assertTrue(downloader.download_audio('https://example.org', '.'))
            self.assertEqual(downloader.last_downloaded_file, 'final.mp3')

    def test_download_exception_reports_failure(self):
        callback = MagicMock()
        with patch('src.video_downloader.yt_dlp.YoutubeDL', side_effect=RuntimeError('network failed')):
            self.assertFalse(VideoDownloader(callback).download_audio('https://example.org', '.'))
        self.assertEqual(callback.call_args.args[0]['error'], 'network failed')

    def test_skipped_duration_cannot_appear_as_completed(self):
        downloader = VideoDownloader()
        self.assertIsNotNone(downloader._duration_filter({'duration': 1801}, incomplete=False))
        self.assertIsNone(downloader._duration_filter({'duration': 1800}, incomplete=False))

    def test_spotify_options_are_usable_without_os_name_error(self):
        downloader = SpotifyDownloader()
        self.addCleanup(downloader._session.close)
        self.assertIn('quiet', downloader._get_base_opts())
        self.assertIsNone(downloader._extract_spotify_id('https://example.org/spotify.com/track/abc'))

    def test_spotify_rejects_failed_download(self):
        downloader = SpotifyDownloader()
        self.addCleanup(downloader._session.close)
        with patch.object(downloader, '_search_youtube', return_value={'id': '123', 'title': 'Song'}), \
             patch('src.spotify_downloader.yt_dlp.YoutubeDL') as factory:
            factory.return_value.__enter__.return_value.download.return_value = 1
            success, message = downloader.download('https://open.spotify.com/track/abc', '.', search_query='Song')
        self.assertFalse(success)
        self.assertIn('archivo', message)

    def test_ffmpeg_failure_propagates_from_postprocessor(self):
        with tempfile.TemporaryDirectory() as directory:
            media = Path(directory) / 'video.mkv'
            media.touch()
            with patch('src.video_downloader.subprocess.run', side_effect=OSError('ffmpeg missing')):
                with self.assertRaises(yt_dlp.utils.PostProcessingError):
                    StripAudioPP().run({'filepath': str(media)})


class ControllerTests(unittest.TestCase):
    def test_error_callback_survives_exception_scope(self):
        ui = MagicMock()
        ui.url_frame.get_url.return_value = 'https://example.org'
        queued = []
        ui.after.side_effect = lambda delay, callback: queued.append(callback)
        controller = DownloadController(ui)
        self.addCleanup(controller.spotify_downloader._session.close)
        with patch.object(controller.video_downloader, 'get_playlist_info', side_effect=RuntimeError('metadata failed')), \
             patch('src.gui.controller.threading.Thread') as thread:
            thread.side_effect = lambda **kwargs: MagicMock(start=kwargs['target'])
            controller.analyze_url()
        for callback in queued:
            callback()
        ui._update_status.assert_any_call('Error: metadata failed', 'error')
        self.assertFalse(controller._is_analyzing)

    def test_duplicate_download_is_ignored(self):
        ui = MagicMock()
        controller = DownloadController(ui)
        self.addCleanup(controller.spotify_downloader._session.close)
        controller._is_downloading = True
        controller.start_download()
        ui.url_frame.get_url.assert_not_called()


if __name__ == '__main__':
    unittest.main()
