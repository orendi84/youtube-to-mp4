#!/usr/bin/env python3

import argparse
import os
import glob
from pathlib import Path

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
    
    output_template = os.path.join(output_path, '%(title)s.%(ext)s')
    
    # Configure options
    if audio_only:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp4',
                'preferredquality': '192',
            }],
            'outtmpl': output_template,
            'quiet': False,
            'progress': True,
            'no_warnings': False,
            # Force extension to be mp4
            'fixup': 'detect_or_warn',
            'postprocessor_args': [
                '-c:a', 'aac',
            ],
            # Clean up intermediate files
            'keepvideo': False,
        }
        print("Audio-only mode: Downloading audio as MP4...")
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
        ydl.download([url])
        
        # If audio-only, ensure we have only mp4 files
        if audio_only:
            # Try to clean up any webm files that might be left
            title = ydl.extract_info(url, download=False).get('title', '').replace('/', '_')
            for webm_file in glob.glob(os.path.join(output_path, f"{title}*.webm")):
                try:
                    os.remove(webm_file)
                    print(f"Cleaned up: {webm_file}")
                except:
                    pass
                    
        print(f"Download complete! {'Audio' if audio_only else 'Video'} saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Download YouTube videos as MP4 files (including audio-only)')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('-o', '--output', help='Output directory (default: ~/Downloads)')
    parser.add_argument('-q', '--quality', default='best', 
                        help='Video quality (best, 1080p, 720p, 480p, 360p, 240p, 144p)')
    parser.add_argument('-a', '--audio-only', action='store_true', 
                        help='Download audio only (as MP4)')
    
    args = parser.parse_args()
    download_video(args.url, args.output, args.quality, args.audio_only)

if __name__ == "__main__":
    main() 