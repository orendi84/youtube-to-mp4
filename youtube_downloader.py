#!/usr/bin/env python3

import argparse
import os
import glob
import time
import shutil
import subprocess
import json
from pathlib import Path

# Default file to store YouTube URL
DEFAULT_URL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtube_url.txt")

def get_audio_duration(file_path, ffmpeg_path):
    """
    Get the duration of an audio file in seconds using ffprobe.
    
    Args:
        file_path: Path to the audio file
        ffmpeg_path: Path to ffmpeg directory
        
    Returns:
        Duration in seconds as float, or None if failed
    """
    # Try multiple locations for ffprobe
    possible_paths = [
        os.path.join(ffmpeg_path, 'ffprobe'),  # Local ffmpeg directory
        '/opt/homebrew/bin/ffprobe',           # Homebrew on Apple Silicon
        '/usr/local/bin/ffprobe',              # Homebrew on Intel Mac
        'ffprobe'                              # System PATH
    ]
    
    ffprobe_path = None
    for path in possible_paths:
        if os.path.exists(path) or path == 'ffprobe':
            ffprobe_path = path
            break
    
    if not ffprobe_path:
        ffprobe_path = 'ffprobe'  # Fallback
    
    try:
        cmd = [
            ffprobe_path,
            '-v', 'quiet',
            '-print_format', 'json',
            '-show_format',
            file_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            duration = float(data['format']['duration'])
            return duration
    except Exception as e:
        print(f"Error getting audio duration: {e}")
    return None

def split_audio_file(file_path, ffmpeg_path, chunk_duration_minutes=35):
    """
    Split an audio file into chunks of specified duration.
    
    Args:
        file_path: Path to the input audio file
        ffmpeg_path: Path to ffmpeg directory
        chunk_duration_minutes: Duration of each chunk in minutes
        
    Returns:
        List of created chunk file paths
    """
    # Try multiple locations for ffmpeg
    possible_paths = [
        os.path.join(ffmpeg_path, 'ffmpeg'),   # Local ffmpeg directory
        '/opt/homebrew/bin/ffmpeg',            # Homebrew on Apple Silicon
        '/usr/local/bin/ffmpeg',               # Homebrew on Intel Mac
        'ffmpeg'                               # System PATH
    ]
    
    ffmpeg_exe = None
    for path in possible_paths:
        if os.path.exists(path) or path == 'ffmpeg':
            ffmpeg_exe = path
            break
    
    if not ffmpeg_exe:
        ffmpeg_exe = 'ffmpeg'  # Fallback
    
    # Get audio duration
    total_duration = get_audio_duration(file_path, ffmpeg_path)
    if total_duration is None:
        print("Could not determine audio duration. Skipping split.")
        return [file_path]
    
    chunk_duration_seconds = chunk_duration_minutes * 60
    total_chunks = int(total_duration / chunk_duration_seconds) + (1 if total_duration % chunk_duration_seconds > 0 else 0)
    
    if total_chunks <= 1:
        print(f"Audio duration ({total_duration/60:.1f} minutes) is less than {chunk_duration_minutes} minutes. No splitting needed.")
        return [file_path]
    
    print(f"Splitting audio into {total_chunks} chunks of {chunk_duration_minutes} minutes each...")
    
    # Prepare file paths
    base_path = os.path.splitext(file_path)[0]
    base_name = os.path.basename(base_path)
    output_dir = os.path.dirname(file_path)
    
    chunk_files = []
    
    for i in range(total_chunks):
        start_time = i * chunk_duration_seconds
        chunk_file = os.path.join(output_dir, f"{base_name}_part{i+1:02d}.mp3")
        
        cmd = [
            ffmpeg_exe,
            '-i', file_path,
            '-ss', str(start_time),
            '-t', str(chunk_duration_seconds),
            '-c', 'copy',
            '-avoid_negative_ts', 'make_zero',
            chunk_file
        ]
        
        try:
            print(f"Creating part {i+1}/{total_chunks}...")
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                chunk_files.append(chunk_file)
                print(f"Created: {os.path.basename(chunk_file)}")
            else:
                print(f"Error creating chunk {i+1}: {result.stderr}")
        except Exception as e:
            print(f"Error splitting audio chunk {i+1}: {e}")
    
    if chunk_files:
        # Remove the original file since we have chunks
        try:
            os.remove(file_path)
            print(f"Removed original file: {os.path.basename(file_path)}")
        except Exception as e:
            print(f"Error removing original file: {e}")
    
    return chunk_files

def download_video(url, output_path=None, quality='best', audio_only=True, split_audio=True):
    
    """
    Download a YouTube video and save it as an MP4 file.
    
    Args:
        url: YouTube video URL
        output_path: Directory to save the video (defaults to Downloads folder)
        quality: Video quality ('best', '1080p', '720p', '480p', etc.)
        audio_only: If True, download only the audio (as MP4)
        split_audio: If True, split audio files into 35-minute chunks
    """
    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp not found. Installing...")
        os.system("pip install yt-dlp")
        import yt_dlp
    
    # Use macOS Downloads folder as default
    if output_path is None:
        output_path = os.path.expanduser("~/Downloads")
    
    os.makedirs(output_path, exist_ok=True)
    
    # Create a temporary directory for downloads
    temp_dir = os.path.join(output_path, f"yt_temp_{int(time.time())}")
    os.makedirs(temp_dir, exist_ok=True)
    
    # Simplified file naming
    output_template = os.path.join(temp_dir, 'download.%(ext)s')
    
    # Configure options
    if audio_only:
        # Download best audio and convert to MP3
        ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_template,
            'quiet': False,
            'progress': True,
            'no_warnings': False,
            'keepvideo': False,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ffmpeg_location': ffmpeg_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        print("Audio-only mode: Downloading and converting to MP3...")
    else:
        # Use single format to avoid ffmpeg requirement
        if quality == 'best':
            format_selector = 'best[ext=mp4]/best'
        else:
            format_selector = f'best[height<={quality[:-1]}][ext=mp4]/best[height<={quality[:-1]}]/best'
        
        ydl_opts = {
            'format': format_selector,
            'outtmpl': output_template,
            'quiet': False,
            'progress': True,
            'no_warnings': False,
        }
        
        # Handle quality formats like '1080p', '720p', etc.
        if quality not in ['best', '1080p', '720p', '480p', '360p', '240p', '144p']:
            print(f"Invalid quality: {quality}. Using 'best' instead.")
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
    
    # Download the video or audio
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"Downloading from: {url}")
        print(f"Target folder: {output_path}")
        
        # Extract information about the video
        info = ydl.extract_info(url, download=True)
        title = info.get('title', 'download').replace('/', '_').replace('|', '_')
        
        # Find the downloaded file
        downloaded_files = os.listdir(temp_dir)
        if not downloaded_files:
            print("Error: No files were downloaded")
            return
            
        downloaded_file = os.path.join(temp_dir, downloaded_files[0])
        
        # Set the final filename and move the file
        final_ext = 'mp3' if audio_only else 'mp4'  # Use MP3 for audio, MP4 for video
        final_filename = f"{title}.{final_ext}"
        final_path = os.path.join(output_path, final_filename)
        
        # If the file already exists, add a timestamp
        if os.path.exists(final_path):
            timestamp = int(time.time())
            final_filename = f"{title}_{timestamp}.{final_ext}"
            final_path = os.path.join(output_path, final_filename)
        
        # Copy the file to the destination with the MP4 extension
        try:
            shutil.copy2(downloaded_file, final_path)
            print(f"Download complete! File saved as: {final_filename}")
            
            # Split audio file if requested and it's an MP3
            if audio_only and split_audio and final_ext == 'mp3':
                ffmpeg_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ffmpeg')
                chunk_files = split_audio_file(final_path, ffmpeg_path)
                if len(chunk_files) > 1:
                    print(f"Audio split into {len(chunk_files)} parts successfully!")
                    for chunk in chunk_files:
                        print(f"  - {os.path.basename(chunk)}")
                        
        except Exception as e:
            print(f"Error copying file: {e}")
        
        # Clean up temporary directory
        try:
            shutil.rmtree(temp_dir)
        except Exception as e:
            print(f"Error cleaning up temp files: {e}")

def read_url_from_file():
    """Read YouTube URL from the default file if it exists."""
    if os.path.exists(DEFAULT_URL_FILE):
        with open(DEFAULT_URL_FILE, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip empty lines and comments
                if line and not line.startswith('#'):
                    # Check if it looks like a URL
                    if 'youtube.com' in line or 'youtu.be' in line:
                        return line
    return None

def main():
    parser = argparse.ArgumentParser(description='Download YouTube videos as MP4 files (including audio-only)')
    parser.add_argument('url', nargs='?', help='YouTube video URL')
    parser.add_argument('-o', '--output', help='Output directory (default: ~/Downloads)')
    parser.add_argument('-q', '--quality', default='best', 
                        help='Video quality (best, 1080p, 720p, 480p, 360p, 240p, 144p)')
    parser.add_argument('-a', '--audio-only', action='store_true', default=True,
                        help='Download audio only (as MP4) - default behavior')
    parser.add_argument('-v', '--video', action='store_true', 
                        help='Download video (overrides default audio-only mode)')
    parser.add_argument('--no-split', action='store_true',
                        help='Do not split audio files into chunks')
    
    args = parser.parse_args()
    
    # If URL is not provided as argument, try to read from file
    url = args.url
    if not url:
        url = read_url_from_file()
        if not url:
            print("No URL provided and no URL found in youtube_url.txt")
            print("Please either provide a URL as an argument or create a file named 'youtube_url.txt' with the URL")
            return
    
    # If --video flag is used, override the default audio-only behavior
    audio_only = args.audio_only and not args.video
    
    # Determine if we should split audio
    split_audio = not args.no_split
    
    download_video(url, args.output, args.quality, audio_only, split_audio)

if __name__ == "__main__":
    main() 