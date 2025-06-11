# YouTube to MP3 Downloader with Auto-Split

A powerful Python tool to download YouTube videos as MP3 files with automatic splitting into 35-minute chunks - perfect for long-form content, podcasts, and music mixes.

## ✨ Features

- **🎵 Audio-only MP3 downloads** - High-quality audio extraction
- **✂️ Automatic MP3 splitting** - Long videos automatically split into 35-minute chunks
- **📁 Smart file management** - Organized output with sequential naming (`part01.mp3`, `part02.mp3`, etc.)
- **🔧 Flexible options** - Download video, audio-only, or disable splitting as needed
- **🚀 Auto-dependency management** - Automatically installs required tools
- **💻 Cross-platform support** - Works on macOS, Linux, and Windows
- **🎯 Multiple input methods** - URL from command line or `youtube_url.txt` file

## 🛠 Installation

### Prerequisites
- Python 3.6+
- FFmpeg (automatically detected or can be installed via Homebrew on macOS)

### Setup
1. Clone this repository:
```bash
git clone https://github.com/orendi84/youtube-to-mp4.git
cd youtube-to-mp4
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. (macOS) Install FFmpeg via Homebrew (recommended):
```bash
brew install ffmpeg
```

## 🚀 Usage

### Quick Start
Put your YouTube URL in `youtube_url.txt` and run:
```bash
python3 youtube_downloader.py
```

### Command Line Options

#### Basic audio download with auto-split:
```bash
python3 youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

#### Download without splitting (single file):
```bash
python3 youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --no-split
```

#### Download video (MP4):
```bash
python3 youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --video
```

#### Custom output directory:
```bash
python3 youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" -o ~/Downloads/music
```

#### Video with quality option:
```bash
python3 youtube_downloader.py "https://www.youtube.com/watch?v=VIDEO_ID" --video -q 1080p
```

## 📋 Command Line Arguments

```
usage: youtube_downloader.py [-h] [-o OUTPUT] [-q QUALITY] [-a] [-v] [--no-split] [url]

positional arguments:
  url                   YouTube video URL

options:
  -h, --help            show this help message and exit
  -o, --output OUTPUT   Output directory (default: ~/Downloads)
  -q, --quality QUALITY
                        Video quality (best, 1080p, 720p, 480p, 360p, 240p, 144p)
  -a, --audio-only      Download audio only (as MP3) - default behavior
  -v, --video           Download video (overrides default audio-only mode)
  --no-split            Do not split audio files into chunks
```

## 🎵 MP3 Splitting Feature

### How it works:
- **Automatic detection**: Videos longer than 35 minutes are automatically split
- **Smart naming**: Files are named sequentially (`video_part01.mp3`, `video_part02.mp3`, etc.)
- **Perfect chunks**: Each part is exactly 35 minutes (except the last part)
- **Efficient processing**: Uses FFmpeg's copy mode for fast, lossless splitting
- **Clean output**: Original file is removed after successful splitting

### Example output:
```
Long Mix (2 hours) →
├── Long Mix_part01.mp3 (35 minutes)
├── Long Mix_part02.mp3 (35 minutes)
├── Long Mix_part03.mp3 (35 minutes)
└── Long Mix_part04.mp3 (15 minutes)
```

## 📝 Using the URL File

Create a `youtube_url.txt` file in the project directory:
```
# Paste your YouTube URL below and save the file
# Then run the script without arguments: python3 youtube_downloader.py

https://www.youtube.com/watch?v=YOUR_VIDEO_ID
```

Then simply run:
```bash
python3 youtube_downloader.py
```

## 🎬 Available Video Quality Options

- `best` (default) - Best available quality
- `1080p` - Full HD
- `720p` - HD  
- `480p` - Standard definition
- `360p` - Low definition
- `240p` - Very low definition
- `144p` - Lowest definition

## 🔧 Technical Details

### FFmpeg Detection
The script automatically detects FFmpeg in multiple locations:
- `/opt/homebrew/bin/` (Homebrew on Apple Silicon)
- `/usr/local/bin/` (Homebrew on Intel Mac)
- Local `ffmpeg` directory
- System PATH

### Dependencies
- `yt-dlp` - YouTube downloading library
- `ffmpeg` - Audio/video processing (auto-detected)
- `ffprobe` - Media information extraction (included with ffmpeg)

## 🎯 Use Cases

- **📻 Podcast episodes** - Split long podcasts into manageable chunks
- **🎼 DJ mixes** - Break down long music sets
- **🎓 Educational content** - Segment lectures and tutorials  
- **📱 Mobile-friendly** - Smaller files for easier transfer and storage
- **🔄 Platform limits** - Work around file size restrictions

## 🐛 Troubleshooting

### FFmpeg not found
If you see "ffprobe not found" errors:
1. Install FFmpeg via Homebrew: `brew install ffmpeg`
2. Or ensure FFmpeg is in your system PATH

### Download fails
- Check your internet connection
- Verify the YouTube URL is valid and public
- Some videos may have regional restrictions

## 📄 License

MIT License - see LICENSE file for details.

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you would like to change. 