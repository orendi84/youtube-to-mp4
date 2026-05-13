"""Smoke tests for youtube_downloader. No network, no ffmpeg required."""

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import youtube_downloader as yd  # noqa: E402


class TestParser(unittest.TestCase):
    def test_defaults(self):
        args = yd.build_parser().parse_args(["https://youtu.be/abc"])
        self.assertEqual(args.url, "https://youtu.be/abc")
        self.assertTrue(args.audio_only)
        self.assertTrue(args.split)
        self.assertEqual(args.chunk_minutes, yd.CHUNK_MINUTES_DEFAULT)
        self.assertEqual(args.quality, "best")
        self.assertFalse(args.verbose)

    def test_no_audio_only(self):
        args = yd.build_parser().parse_args(["--no-audio-only", "https://youtu.be/abc"])
        self.assertFalse(args.audio_only)

    def test_no_split(self):
        args = yd.build_parser().parse_args(["--no-split", "https://youtu.be/abc"])
        self.assertFalse(args.split)

    def test_chunk_minutes(self):
        args = yd.build_parser().parse_args(["--chunk-minutes", "20", "https://youtu.be/abc"])
        self.assertEqual(args.chunk_minutes, 20)

    def test_invalid_quality_passes_through(self):
        # Validation happens in select_format, not the parser.
        args = yd.build_parser().parse_args(["-q", "garbage", "https://youtu.be/abc"])
        self.assertEqual(args.quality, "garbage")


class TestSelectFormat(unittest.TestCase):
    def test_best(self):
        self.assertEqual(yd.select_format("best"), "best[ext=mp4]/best")

    def test_720p(self):
        fmt = yd.select_format("720p")
        self.assertIn("height<=720", fmt)
        self.assertIn("[ext=mp4]", fmt)

    def test_invalid_falls_back_to_best(self):
        self.assertEqual(yd.select_format("999p"), "best[ext=mp4]/best")
        self.assertEqual(yd.select_format("garbage"), "best[ext=mp4]/best")
        self.assertEqual(yd.select_format(""), "best[ext=mp4]/best")


class TestFindBinary(unittest.TestCase):
    def test_prefers_local(self):
        local_path = str(Path(yd.__file__).resolve().parent / "ffmpeg" / "ffmpeg")

        def fake_exists(p):
            return p == local_path

        with mock.patch("youtube_downloader.os.path.isfile", side_effect=fake_exists), \
             mock.patch("youtube_downloader.os.access", return_value=True):
            self.assertEqual(yd.find_binary("ffmpeg"), local_path)

    def test_falls_back_to_which(self):
        with mock.patch("youtube_downloader.os.path.isfile", return_value=False), \
             mock.patch("youtube_downloader.shutil.which", return_value="/fake/bin/ffmpeg"):
            self.assertEqual(yd.find_binary("ffmpeg"), "/fake/bin/ffmpeg")

    def test_returns_none_when_missing(self):
        with mock.patch("youtube_downloader.os.path.isfile", return_value=False), \
             mock.patch("youtube_downloader.shutil.which", return_value=None):
            self.assertIsNone(yd.find_binary("ffmpeg"))

    def test_skips_non_executable_file(self):
        """A local file that exists but isn't executable must be skipped (not picked then crash later)."""
        with tempfile.TemporaryDirectory() as tmp:
            non_exec = Path(tmp) / "ffmpeg"
            non_exec.write_text("# not actually ffmpeg")
            non_exec.chmod(0o644)  # readable, NOT executable

            def fake_isfile(p):
                return p == str(non_exec)

            def fake_access(p, mode):
                # Only the real non-executable file we created exists; never executable.
                return False

            with mock.patch("youtube_downloader.os.path.isfile", side_effect=fake_isfile), \
                 mock.patch("youtube_downloader.os.access", side_effect=fake_access), \
                 mock.patch("youtube_downloader.shutil.which", return_value="/usr/bin/ffmpeg"):
                # Should NOT return the non-executable local file; should fall through to which()
                self.assertEqual(yd.find_binary("ffmpeg"), "/usr/bin/ffmpeg")


class TestReadUrlFromFile(unittest.TestCase):
    def test_skips_comments_and_returns_url(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "youtube_url.txt"
            path.write_text("# a comment\n\nhttps://www.youtube.com/watch?v=abc123\n")
            with mock.patch.object(yd, "DEFAULT_URL_FILE", path):
                self.assertEqual(
                    yd.read_url_from_file(),
                    "https://www.youtube.com/watch?v=abc123",
                )

    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(yd, "DEFAULT_URL_FILE", Path(tmp) / "nope.txt"):
                self.assertIsNone(yd.read_url_from_file())

    def test_no_url_in_file_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "youtube_url.txt"
            path.write_text("# only comments\n\n# another comment\n")
            with mock.patch.object(yd, "DEFAULT_URL_FILE", path):
                self.assertIsNone(yd.read_url_from_file())

    def test_tolerates_non_utf8_bytes(self):
        """A stray non-UTF-8 byte must not crash; the URL on a clean line is still picked up."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "youtube_url.txt"
            path.write_bytes(b"# smart-quoted intro \x93garbled\x94\nhttps://www.youtube.com/watch?v=abc\n")
            with mock.patch.object(yd, "DEFAULT_URL_FILE", path):
                self.assertEqual(
                    yd.read_url_from_file(),
                    "https://www.youtube.com/watch?v=abc",
                )


class TestSplitAudioFile(unittest.TestCase):
    def test_chunk_minutes_reaches_ffmpeg(self):
        """split_audio_file must pass chunk_minutes*60 to ffmpeg's -t flag."""
        captured_cmds = []

        def fake_run(cmd, *args, **kwargs):
            captured_cmds.append(cmd)
            return mock.Mock(returncode=0, stderr="")

        with mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"), \
             mock.patch.object(yd.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(yd.os, "remove"):
            chunks = yd.split_audio_file(
                "/tmp/fake.mp3",
                chunk_minutes=20,
                known_duration=50 * 60,  # 50 minutes -> expect 3 chunks at 20 min
            )

        self.assertEqual(len(chunks), 3)
        # Every ffmpeg invocation should request -t 1200 (20 * 60)
        for cmd in captured_cmds:
            self.assertIn("-t", cmd)
            self.assertEqual(cmd[cmd.index("-t") + 1], "1200")
        # Perf-1: -ss must come BEFORE -i (input seeking, not output seeking)
        # for at least one chunk so ffmpeg seeks at file level (O(N) total work).
        self.assertTrue(any(cmd.index("-ss") < cmd.index("-i") for cmd in captured_cmds))

    def test_partial_failure_keeps_original(self):
        """If any chunk fails, the original file must NOT be deleted (data loss)."""
        remove_calls = []
        call_count = {"n": 0}

        def fake_run(cmd, *args, **kwargs):
            call_count["n"] += 1
            # First chunk succeeds, second fails
            if call_count["n"] == 1:
                return mock.Mock(returncode=0, stderr="")
            return mock.Mock(returncode=1, stderr="ffmpeg error")

        with mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"), \
             mock.patch.object(yd.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(yd.os, "remove", side_effect=lambda p: remove_calls.append(p)):
            chunks = yd.split_audio_file(
                "/tmp/fake.mp3",
                chunk_minutes=35,
                known_duration=80 * 60,  # 80 min -> 3 chunks expected
            )

        self.assertEqual(len(chunks), 1)  # only first succeeded
        self.assertEqual(remove_calls, [])  # original NOT removed

    def test_all_success_removes_original(self):
        remove_calls = []
        with mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"), \
             mock.patch.object(
                 yd.subprocess, "run",
                 return_value=mock.Mock(returncode=0, stderr=""),
             ), \
             mock.patch.object(yd.os, "remove", side_effect=lambda p: remove_calls.append(p)):
            chunks = yd.split_audio_file(
                "/tmp/fake.mp3",
                chunk_minutes=35,
                known_duration=80 * 60,
            )
        self.assertEqual(len(chunks), 3)
        self.assertEqual(remove_calls, ["/tmp/fake.mp3"])

    def test_no_split_when_under_threshold(self):
        with mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"):
            chunks = yd.split_audio_file(
                "/tmp/fake.mp3",
                chunk_minutes=35,
                known_duration=10 * 60,  # 10 min < 35 min
            )
        self.assertEqual(chunks, ["/tmp/fake.mp3"])

    def test_no_split_when_ffmpeg_missing(self):
        with mock.patch.object(yd, "find_binary", return_value=None):
            chunks = yd.split_audio_file("/tmp/fake.mp3", known_duration=99 * 60)
        self.assertEqual(chunks, ["/tmp/fake.mp3"])

    def test_ffprobe_timeout_returns_none(self):
        """If ffprobe hangs and TimeoutExpired fires, get_audio_duration returns None."""
        def fake_run(cmd, *args, **kwargs):
            raise yd.subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 60))

        with mock.patch.object(yd, "find_binary", return_value="/fake/ffprobe"), \
             mock.patch.object(yd.subprocess, "run", side_effect=fake_run):
            self.assertIsNone(yd.get_audio_duration("/tmp/fake.mp3"))

    def test_ffmpeg_chunk_timeout_aborts_split_preserves_original(self):
        """First chunk times out -> exactly 1 subprocess call, original kept, returns [file_path]."""
        run_calls = []
        remove_calls = []

        def fake_run(cmd, *args, **kwargs):
            run_calls.append(cmd)
            raise yd.subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout", 600))

        with mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"), \
             mock.patch.object(yd.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(yd.os, "remove", side_effect=lambda p: remove_calls.append(p)):
            chunks = yd.split_audio_file(
                "/tmp/fake.mp3",
                chunk_minutes=35,
                known_duration=5 * 35 * 60,  # 5 chunks worth
            )

        self.assertEqual(len(run_calls), 1)  # aborted on first timeout, no continuation
        self.assertEqual(remove_calls, [])  # original NOT removed
        # Zero chunks succeeded -> contract fix returns [file_path]
        self.assertEqual(chunks, ["/tmp/fake.mp3"])

    def test_all_chunks_fail_returns_original_path_not_empty_list(self):
        """Contract fix: when every chunk's ffmpeg call fails, return [file_path], NOT []."""
        remove_calls = []

        def fake_run(cmd, *args, **kwargs):
            return mock.Mock(returncode=1, stderr="ffmpeg error")

        with mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"), \
             mock.patch.object(yd.subprocess, "run", side_effect=fake_run), \
             mock.patch.object(yd.os, "remove", side_effect=lambda p: remove_calls.append(p)):
            chunks = yd.split_audio_file(
                "/tmp/fake.mp3",
                chunk_minutes=35,
                known_duration=80 * 60,  # 80 min -> 3 chunks expected
            )

        self.assertEqual(chunks, ["/tmp/fake.mp3"])
        self.assertEqual(remove_calls, [])  # original NOT removed


class TestDownloadExtensionHandling(unittest.TestCase):
    """End-to-end mock tests that catch extension-lying bugs in download()."""

    def _run_with_fake_ytdlp(self, produced_ext: str, audio_only: bool, quality: str = "best"):
        """Run download() with a fake yt-dlp that drops download.<produced_ext> in temp."""
        import yt_dlp as real_yt_dlp  # to grab real sanitize_filename + DownloadError

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download):
                tmpl = self.opts["outtmpl"]
                tmp_dir = os.path.dirname(tmpl)
                fake_file = os.path.join(tmp_dir, f"download.{produced_ext}")
                Path(fake_file).touch()
                return {"title": "Test Video : With | Special Chars", "duration": 120}

        fake_yt_dlp = mock.MagicMock()
        fake_yt_dlp.YoutubeDL = FakeYDL
        fake_yt_dlp.utils.sanitize_filename = real_yt_dlp.utils.sanitize_filename
        fake_yt_dlp.utils.DownloadError = real_yt_dlp.utils.DownloadError

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}), \
                 mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"):
                return yd.download(
                    url="https://fake.invalid/v",
                    output_dir=tmp,
                    quality=quality,
                    audio_only=audio_only,
                    split=False,
                )

    def test_video_mode_webm_saved_as_webm_not_mp4(self):
        """If yt-dlp produces .webm in video mode, final file is .webm — NOT a lying .mp4."""
        result = self._run_with_fake_ytdlp(produced_ext="webm", audio_only=False, quality="720p")
        self.assertIsNotNone(result)
        self.assertEqual(result.suffix, ".webm")

    def test_video_mode_mp4_saved_as_mp4(self):
        result = self._run_with_fake_ytdlp(produced_ext="mp4", audio_only=False, quality="720p")
        self.assertIsNotNone(result)
        self.assertEqual(result.suffix, ".mp4")

    def test_audio_mode_mp3_saved_as_mp3(self):
        result = self._run_with_fake_ytdlp(produced_ext="mp3", audio_only=True)
        self.assertIsNotNone(result)
        self.assertEqual(result.suffix, ".mp3")

    def test_audio_mode_uses_correct_format_and_calls_split(self):
        """Audio path: ydl_opts['format']='bestaudio/best', split_audio_file called with known_duration."""
        import yt_dlp as real_yt_dlp

        captured_opts = []
        split_calls = []

        class FakeYDL:
            def __init__(self, opts):
                captured_opts.append(opts)
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download):
                tmp_dir = os.path.dirname(self.opts["outtmpl"])
                Path(os.path.join(tmp_dir, "download.mp3")).touch()
                return {"title": "Audio Test", "duration": 4200}

        fake_yt_dlp = mock.MagicMock()
        fake_yt_dlp.YoutubeDL = FakeYDL
        fake_yt_dlp.utils.sanitize_filename = real_yt_dlp.utils.sanitize_filename
        fake_yt_dlp.utils.DownloadError = real_yt_dlp.utils.DownloadError

        def fake_split(file_path, chunk_minutes=35, known_duration=None):
            split_calls.append({
                "file_path": file_path,
                "chunk_minutes": chunk_minutes,
                "known_duration": known_duration,
            })
            return [file_path]

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}), \
                 mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"), \
                 mock.patch.object(yd, "split_audio_file", side_effect=fake_split):
                result = yd.download(
                    url="https://fake.invalid/v",
                    output_dir=tmp,
                    audio_only=True,
                    split=True,
                    chunk_minutes=35,
                )

        self.assertIsNotNone(result)
        self.assertEqual(result.suffix, ".mp3")
        self.assertEqual(captured_opts[0]["format"], "bestaudio/best")
        self.assertEqual(len(split_calls), 1)
        self.assertEqual(split_calls[0]["known_duration"], 4200)
        self.assertEqual(split_calls[0]["chunk_minutes"], 35)

    def test_video_mode_does_not_call_split(self):
        split_calls = []
        with mock.patch.object(yd, "split_audio_file", side_effect=lambda *a, **k: split_calls.append(1)):
            result = self._run_with_fake_ytdlp(produced_ext="mp4", audio_only=False, quality="720p")
        self.assertIsNotNone(result)
        self.assertEqual(split_calls, [])


class TestDownloadCollisionAndMissingFile(unittest.TestCase):
    """Coverage for download()'s collision suffix branch and the no-matching-file branch."""

    def _make_fake_yt_dlp(self, produced_ext: str = "mp3", title: str = "Test Video"):
        import yt_dlp as real_yt_dlp

        class FakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download):
                tmp_dir = os.path.dirname(self.opts["outtmpl"])
                Path(os.path.join(tmp_dir, f"download.{produced_ext}")).touch()
                return {"title": title, "duration": 60}

        fake = mock.MagicMock()
        fake.YoutubeDL = FakeYDL
        fake.utils.sanitize_filename = real_yt_dlp.utils.sanitize_filename
        fake.utils.DownloadError = real_yt_dlp.utils.DownloadError
        return fake

    def test_collision_appends_counter_suffix(self):
        """If Test_Video.mp3 exists, downloaded file lands at Test_Video_1.mp3."""
        fake_yt_dlp = self._make_fake_yt_dlp(produced_ext="mp3", title="Test Video")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "Test_Video.mp3").write_text("pre-existing")
            with mock.patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}), \
                 mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"):
                result = yd.download(
                    url="https://fake.invalid/v",
                    output_dir=str(out),
                    audio_only=True,
                    split=False,
                )
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "Test_Video_1.mp3")
            self.assertTrue(result.exists())

    def test_double_collision_increments_counter(self):
        """If Test_Video.mp3 and Test_Video_1.mp3 both exist, lands at Test_Video_2.mp3."""
        fake_yt_dlp = self._make_fake_yt_dlp(produced_ext="mp3", title="Test Video")
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / "Test_Video.mp3").write_text("pre-existing-a")
            (out / "Test_Video_1.mp3").write_text("pre-existing-b")
            with mock.patch.dict(sys.modules, {"yt_dlp": fake_yt_dlp}), \
                 mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"):
                result = yd.download(
                    url="https://fake.invalid/v",
                    output_dir=str(out),
                    audio_only=True,
                    split=False,
                )
            self.assertIsNotNone(result)
            self.assertEqual(result.name, "Test_Video_2.mp3")
            self.assertTrue(result.exists())

    def test_no_matching_file_in_temp_dir_returns_none(self):
        """FakeYDL succeeds but produces no download.* file — download() must return None."""
        import yt_dlp as real_yt_dlp

        class EmptyFakeYDL:
            def __init__(self, opts):
                self.opts = opts

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                return False

            def extract_info(self, url, download):
                # Note: do NOT create any download.* file in temp_dir.
                return {"title": "Nothing", "duration": 30}

        fake = mock.MagicMock()
        fake.YoutubeDL = EmptyFakeYDL
        fake.utils.sanitize_filename = real_yt_dlp.utils.sanitize_filename
        fake.utils.DownloadError = real_yt_dlp.utils.DownloadError

        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.dict(sys.modules, {"yt_dlp": fake}), \
                 mock.patch.object(yd, "find_binary", return_value="/fake/ffmpeg"):
                result = yd.download(
                    url="https://fake.invalid/v",
                    output_dir=tmp,
                    audio_only=True,
                    split=False,
                )
            self.assertIsNone(result)


class TestMain(unittest.TestCase):
    def test_returns_2_when_no_url(self):
        with mock.patch.object(sys, "argv", ["youtube_downloader.py"]), \
             mock.patch.object(yd, "read_url_from_file", return_value=None):
            self.assertEqual(yd.main(), 2)

    def test_returns_2_when_chunk_minutes_invalid(self):
        with mock.patch.object(
            sys, "argv",
            ["youtube_downloader.py", "--chunk-minutes", "0", "https://youtu.be/abc"],
        ):
            self.assertEqual(yd.main(), 2)


if __name__ == "__main__":
    unittest.main()
