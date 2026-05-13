#!/usr/bin/env python3
"""Download a YouTube video as MP3 (default) or MP4, with optional MP3 splitting."""

from __future__ import annotations

import argparse
import glob
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

__version__ = "0.2.0"

CHUNK_MINUTES_DEFAULT = 35
AUDIO_BITRATE_KBPS = 192
VALID_QUALITIES = {"best", "1080p", "720p", "480p", "360p", "240p", "144p"}
DEFAULT_URL_FILE = Path(__file__).resolve().parent / "youtube_url.txt"

log = logging.getLogger("yt2mp3")


# --- helpers ---------------------------------------------------------------

def find_binary(name: str) -> Optional[str]:
    """Locate an ffmpeg-family binary, preferring local then Homebrew then PATH."""
    local = Path(__file__).resolve().parent / "ffmpeg" / name
    candidates = [
        str(local),
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
    ]
    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path
    return shutil.which(name)


def get_audio_duration(file_path: str) -> Optional[float]:
    """Return audio duration in seconds via ffprobe, or None if unavailable."""
    ffprobe = find_binary("ffprobe")
    if not ffprobe:
        log.debug("ffprobe not found; cannot probe duration")
        return None
    try:
        result = subprocess.run(
            [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", file_path],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            log.debug("ffprobe exited %d: %s", result.returncode, result.stderr)
            return None
        return float(json.loads(result.stdout)["format"]["duration"])
    except (json.JSONDecodeError, KeyError, ValueError) as exc:
        log.debug("Could not parse ffprobe output: %s", exc)
        return None


def select_format(quality: str) -> str:
    """Build a yt-dlp format selector for video downloads. Falls back to 'best'."""
    if quality not in VALID_QUALITIES:
        log.warning("Invalid quality %r, using 'best'", quality)
        quality = "best"
    if quality == "best":
        return "best[ext=mp4]/best"
    height = quality.rstrip("p")
    return f"best[height<={height}][ext=mp4]/best[height<={height}]/best"


def split_audio_file(
    file_path: str,
    chunk_minutes: int = CHUNK_MINUTES_DEFAULT,
    known_duration: Optional[float] = None,
) -> list[str]:
    """Split an MP3 into fixed-duration chunks. Returns chunk paths or [original] if no split."""
    ffmpeg = find_binary("ffmpeg")
    if not ffmpeg:
        log.warning("ffmpeg not found; skipping split")
        return [file_path]

    duration = known_duration if known_duration is not None else get_audio_duration(file_path)
    if duration is None:
        log.warning("Could not determine audio duration; skipping split")
        return [file_path]

    chunk_seconds = chunk_minutes * 60
    total_chunks = int(duration // chunk_seconds) + (1 if duration % chunk_seconds > 0 else 0)
    if total_chunks <= 1:
        log.info("Audio is %.1f min; under %d min threshold, no split", duration / 60, chunk_minutes)
        return [file_path]

    log.info("Splitting into %d chunks of %d min each", total_chunks, chunk_minutes)
    base = Path(file_path)
    chunks: list[str] = []
    for i in range(total_chunks):
        start = i * chunk_seconds
        chunk_path = str(base.with_name(f"{base.stem}_part{i+1:02d}{base.suffix}"))
        cmd = [
            ffmpeg,
            "-ss", str(start),
            "-i", file_path,
            "-t", str(chunk_seconds),
            "-c", "copy",
            "-avoid_negative_ts", "make_zero",
            "-y",
            chunk_path,
        ]
        log.info("Creating part %d/%d", i + 1, total_chunks)
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            chunks.append(chunk_path)
            log.info("Created: %s", os.path.basename(chunk_path))
        else:
            log.error("Failed chunk %d: %s", i + 1, result.stderr.strip())

    if not chunks:
        log.warning("All chunks failed; keeping original at %s", file_path)
        return [file_path]
    if len(chunks) == total_chunks:
        try:
            os.remove(file_path)
            log.info("Removed original: %s", os.path.basename(file_path))
        except OSError as exc:
            log.warning("Could not remove original: %s", exc)
    else:
        log.warning(
            "Only %d/%d chunks succeeded; keeping original at %s",
            len(chunks), total_chunks, file_path,
        )
    return chunks


# --- core ------------------------------------------------------------------

def download(
    url: str,
    output_dir: Optional[str] = None,
    quality: str = "best",
    audio_only: bool = True,
    split: bool = True,
    chunk_minutes: int = CHUNK_MINUTES_DEFAULT,
) -> Optional[Path]:
    """Download a YouTube URL. Returns the final output path (or None on hard failure)."""
    try:
        import yt_dlp
    except ImportError:
        log.error("yt-dlp not installed. Run: pip install -r requirements.txt")
        return None

    out = Path(output_dir).expanduser() if output_dir else Path.home() / "Downloads"
    out.mkdir(parents=True, exist_ok=True)

    temp_dir = Path(tempfile.mkdtemp(prefix="yt_temp_", dir=str(out)))
    final_ext = "mp3" if audio_only else "mp4"
    output_template = str(temp_dir / "download.%(ext)s")

    common_opts = {
        "outtmpl": output_template,
        "quiet": False,
        "progress": True,
        "no_warnings": False,
        "retries": 5,
        "fragment_retries": 5,
        "restrictfilenames": True,
    }
    ffmpeg_bin = find_binary("ffmpeg")
    if ffmpeg_bin:
        common_opts["ffmpeg_location"] = ffmpeg_bin
        log.debug("Using ffmpeg at: %s", ffmpeg_bin)
    else:
        log.warning("ffmpeg not found by detector; yt-dlp will try its own search")

    if audio_only:
        ydl_opts = {
            **common_opts,
            "format": "bestaudio/best",
            "keepvideo": False,
            "writethumbnail": False,
            "writesubtitles": False,
            "writeautomaticsub": False,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": str(AUDIO_BITRATE_KBPS),
            }],
        }
        log.info("Audio-only mode: downloading and converting to MP3")
    else:
        ydl_opts = {**common_opts, "format": select_format(quality)}
        log.info("Video mode: quality=%s", quality)

    try:
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                log.info("Downloading from: %s", url)
                log.info("Target folder: %s", out)
                info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as exc:
            log.error("Download failed: %s", exc)
            return None

        raw_title = info.get("title") or "download"
        title = yt_dlp.utils.sanitize_filename(raw_title, restricted=True) or "download"
        duration = info.get("duration")

        matches = sorted(glob.glob(str(temp_dir / f"download.{final_ext}")))
        if not matches:
            # Some post-processors emit a different ext; fall back to any download.*
            matches = sorted(
                p for p in glob.glob(str(temp_dir / "download.*"))
                if not p.endswith((".part", ".info.json", ".ytdl"))
            )
        if not matches:
            log.error("No downloaded file found in temp dir")
            return None

        downloaded = matches[0]
        actual_ext = Path(downloaded).suffix.lstrip(".") or final_ext
        if actual_ext != final_ext:
            log.warning(
                "Expected .%s but yt-dlp produced .%s; saving as .%s",
                final_ext, actual_ext, actual_ext,
            )
        final_path = out / f"{title}.{actual_ext}"
        suffix = 1
        candidate = final_path
        while candidate.exists():
            candidate = out / f"{title}_{suffix}.{actual_ext}"
            suffix += 1
        final_path = candidate

        shutil.move(downloaded, final_path)
        log.info("Saved: %s", final_path.name)

        if audio_only and split and final_path.suffix == ".mp3":
            chunks = split_audio_file(
                str(final_path),
                chunk_minutes=chunk_minutes,
                known_duration=duration,
            )
            if len(chunks) > 1:
                log.info("Audio split into %d parts:", len(chunks))
                for c in chunks:
                    log.info("  - %s", os.path.basename(c))

        return final_path
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# --- cli -------------------------------------------------------------------

def read_url_from_file() -> Optional[str]:
    """Read the first non-comment YouTube URL from the default URL file."""
    if not DEFAULT_URL_FILE.exists():
        return None
    for raw in DEFAULT_URL_FILE.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "youtube.com" in line or "youtu.be" in line:
            return line
    return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download a YouTube video as MP3 (default) or MP4."
    )
    parser.add_argument("url", nargs="?", help="YouTube video URL")
    parser.add_argument("-o", "--output", help="Output directory (default: ~/Downloads)")
    parser.add_argument(
        "-q", "--quality", default="best",
        help=f"Video quality, one of: {', '.join(sorted(VALID_QUALITIES))}",
    )
    parser.add_argument(
        "--audio-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Download audio as MP3 (default). Use --no-audio-only for video.",
    )
    parser.add_argument(
        "--no-split", dest="split", action="store_false",
        help="Do not split long MP3s into chunks",
    )
    parser.add_argument(
        "--chunk-minutes", type=int, default=CHUNK_MINUTES_DEFAULT,
        help=f"Chunk size in minutes when splitting (default: {CHUNK_MINUTES_DEFAULT})",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose logging")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(message)s",
    )

    url = args.url or read_url_from_file()
    if not url:
        log.error(
            "No URL provided and no URL found in %s. "
            "Pass a URL as an argument or add one to youtube_url.txt.",
            DEFAULT_URL_FILE.name,
        )
        return 2

    if args.chunk_minutes <= 0:
        log.error("--chunk-minutes must be positive")
        return 2

    result = download(
        url=url,
        output_dir=args.output,
        quality=args.quality,
        audio_only=args.audio_only,
        split=args.split,
        chunk_minutes=args.chunk_minutes,
    )
    return 0 if result else 1


if __name__ == "__main__":
    sys.exit(main())
