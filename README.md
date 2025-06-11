# YouTube to MP4 Converter

A simple Python tool to download YouTube videos as MP4 files or extract audio as MP3.

## Features

- Download YouTube videos in various quality settings
- Extract audio-only as MP3 files
- Simple command-line interface
- Automatically installs dependencies if needed
- Specify custom output directory

## Installation

1. Clone this repository:
```
git clone https://github.com/orendi84/youtube-to-mp4.git
cd youtube-to-mp4
```

2. Install dependencies:
```
pip install -r requirements.txt
```

## Usage

### Basic usage (video):
```
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Audio-only mode (extracts MP3):
```
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --audio-only
```

### With quality option (for video):
```
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 1080p
```

### With custom output directory:
```
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -o ~/Downloads/videos
```

### All options combined:
```
python youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -q 720p -o ~/Downloads/videos
```

## Available Quality Options (for video)

- `best` (default) - Best available quality
- `1080p` - Full HD
- `720p` - HD
- `480p` - Standard definition
- `360p` - Low definition
- `240p` - Very low definition
- `144p` - Lowest definition

## Requirements

- Python 3.6+
- yt-dlp library (automatically installed if missing)
- FFmpeg (required for audio extraction)

## License

MIT 