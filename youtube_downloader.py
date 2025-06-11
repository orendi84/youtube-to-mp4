#!/usr/bin/env python3

import argparse
import os
import glob
import time
import shutil
from pathlib import Path

# Default file to store YouTube URL
DEFAULT_URL_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "youtube_url.txt")

def download_video(url, output_path=None, quality='best', audio_only=False):
    """
    Download a YouTube video and save it as an MP4 file.
    
    Args:
        url: YouTube video URL
        output_path: Directory to save the video (defaults to Downloads folder)
        quality: Video quality ('best', '1080p', '720p', '480p', etc.)
        audio_only: If True, download only the audio (as MP4)
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
        # Direct download of m4a file (will be moved to MP4 later)
        ydl_opts = {
            'format': 'm4a/bestaudio/best',
            'outtmpl': output_template,
            'quiet': False,
            'progress': True,
            'no_warnings': False,
            'keepvideo': False,
            'writethumbnail': False,
            'writesubtitles': False,
            'writeautomaticsub': False,
        }
        print("Audio-only mode: Downloading audio...")
    else:
        ydl_opts = {
            'format': f'bestvideo[height<={quality[:-1]}]+bestaudio/best' if quality != 'best' else 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
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
        final_ext = 'mp4'  # Always use MP4 extension
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
            url = f.read().strip()
            if url:
                return url
    return None

def main():
    parser = argparse.ArgumentParser(description='Download YouTube videos as MP4 files (including audio-only)')
    parser.add_argument('url', nargs='?', help='YouTube video URL')
    parser.add_argument('-o', '--output', help='Output directory (default: ~/Downloads)')
    parser.add_argument('-q', '--quality', default='best', 
                        help='Video quality (best, 1080p, 720p, 480p, 360p, 240p, 144p)')
    parser.add_argument('-a', '--audio-only', action='store_true', 
                        help='Download audio only (as MP4)')
    
    args = parser.parse_args()
    
    # If URL is not provided as argument, try to read from file
    url = args.url
    if not url:
        url = read_url_from_file()
        if not url:
            print("No URL provided and no URL found in youtube_url.txt")
            print("Please either provide a URL as an argument or create a file named 'youtube_url.txt' with the URL")
            return
    
    download_video(url, args.output, args.quality, args.audio_only)

if __name__ == "__main__":
    main() 