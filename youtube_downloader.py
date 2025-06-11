#!/usr/bin/env python3
import argparse
import os
from pathlib import Path

def download_video(url, output_path=None, quality='best'):
    """
    Download a YouTube video and save it as an MP4 file.
    
    Args:
        url: YouTube video URL
        output_path: Directory to save the video (defaults to current directory)
        quality: Video quality ('best', '1080p', '720p', '480p', etc.)
    """
    try:
        import yt_dlp
    except ImportError:
        print("yt-dlp not found. Installing...")
        os.system("pip install yt-dlp")
        import yt_dlp
    
    if output_path:
        os.makedirs(output_path, exist_ok=True)
    else:
        output_path = os.getcwd()
    
    output_template = os.path.join(output_path, '%(title)s.%(ext)s')
    
    # Configure options
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
    
    # Download the video
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print(f"Downloading video from: {url}")
        ydl.download([url])
        print(f"Download complete! Video saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Download YouTube videos as MP4 files')
    parser.add_argument('url', help='YouTube video URL')
    parser.add_argument('-o', '--output', help='Output directory (default: current directory)')
    parser.add_argument('-q', '--quality', default='best', 
                        help='Video quality (best, 1080p, 720p, 480p, 360p, 240p, 144p)')
    
    args = parser.parse_args()
    download_video(args.url, args.output, args.quality)

if __name__ == "__main__":
    main() 