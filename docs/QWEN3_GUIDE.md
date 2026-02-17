# Qwen3 Audiobook Converter Guide

Complete guide for using the Qwen3-based audiobook converter.

## Overview

The Qwen3 Audiobook Converter is the flagship application in this suite. It uses the **Qwen3 TTS model** running locally to convert PDFs, EPUBs, DOCX, DOC, and TXT files into high-quality audiobooks.

## Features

- 🎤 **Dual Voice Modes**
  - **Custom Voice**: Pre-built high-quality speakers (Ryan, Serena, Aiden, etc.)
  - **Voice Clone**: Clone any voice from a reference audio sample
- 📚 **Multi-Format Support**: TXT, PDF, EPUB, DOCX, DOC
- 🤖 **Always 1.7B Model**: Uses the highest quality model for best results
- 🔄 **Smart Chunking**: Intelligent text splitting with sentence boundary detection
- 💾 **Intelligent Caching**: Avoids re-processing identical chunks
- 🔁 **Robust Error Handling**: Automatic retries and graceful failure recovery
- 📊 **Progress Tracking**: Real-time conversion progress with time estimates
- 🧹 **Auto Cleanup**: Automatic cleanup of temporary files

## Quick Start

### Prerequisites

1. **Qwen Voice Model** running locally
   - Download and run the Qwen3 TTS Gradio interface
   - Server should be accessible at `http://127.0.0.1:7860`
2. **Python 3.8+** with pip
3. **FFmpeg** - Required for audio processing

### Installation

```bash
# Install Python dependencies
pip install -r requirements.txt

# Install FFmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
# Windows: Download from ffmpeg.org
```

### Usage

```bash
# Place your book in the book_to_convert folder
cp your_book.pdf book_to_convert/

# Run the converter (from project root)
python src/audiobook_converter.py

# Output will be in: audiobooks/your_book.mp3
```

## Configuration

### Location

Configuration is stored in two places:
1. **Main config**: `src/config.py` - Core settings
2. **Voice configs**: `config/` - Voice design and chapter configs

### Voice Modes

#### Custom Voice Mode (Default)

Uses pre-built speakers. Edit `src/config.py`:

```python
VOICE_MODE = "custom_voice"
CUSTOM_VOICE_SPEAKER = "Ryan"  # Options: Ryan, Serena, Aiden, Dylan, Eric, Ono_anna, Sohee, Uncle_fu, Vivian
CUSTOM_VOICE_LANGUAGE = "English"
```

**Available Speakers:**
- `Ryan` - Male, clear and professional (default)
- `Serena` - Female, warm and friendly
- `Aiden` - Male, energetic
- `Dylan` - Male, calm
- `Eric` - Male, expressive
- `Ono_anna` - Female, Japanese accent
- `Sohee` - Female, Korean accent
- `Uncle_fu` - Male, Chinese accent
- `Vivian` - Female, versatile

#### Voice Clone Mode

Clone a specific voice from reference audio:

```python
VOICE_MODE = "voice_clone"
VOICE_CLONE_REF_AUDIO = "path/to/reference.wav"
VOICE_CLONE_REF_TEXT = "Text spoken in the reference audio"
```

#### Voice Design Mode

Describe the voice you want:

```python
VOICE_MODE = "voice_design"
```

Edit `config/voicedesign_american_male.yaml`:

```yaml
voice:
  slug: american_male
  language: English
  instruct: >
    Adult American male, professional audiobook narrator.
    Clear enunciation, calm and authoritative tone.
```

### Processing Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `CHUNK_SIZE_WORDS` | 1200 | Words per processing chunk |
| `MAX_WORKERS` | 1 | Concurrent chunks (keep at 1) |
| `AUDIO_FORMAT` | mp3 | Output format |
| `AUDIO_BITRATE` | 128k | Audio quality |
| `MAX_RETRIES` | 3 | Retry attempts for failed chunks |

## Project Structure

```
Qwen3-Audiobook-Converter/
├── src/
│   ├── audiobook_converter.py    # Main conversion script
│   ├── config.py                 # Configuration
│   ├── mlx_tts_engine.py         # MLX TTS implementation
│   └── ...
├── config/
│   ├── chapters.yaml             # Chapter definitions
│   └── voicedesign_*.yaml        # Voice design configs
├── book_to_convert/              # Input folder
├── audiobooks/                   # Output folder
├── cache/                        # Cached audio chunks
├── chunks/                       # Temporary processing files
└── logs/                         # Processing logs
```

## Troubleshooting

### Qwen API Connection Failed

```
[ERROR] Cannot connect to Qwen API!
```

**Solutions:**
- Ensure Qwen Gradio server is running
- Check if server is accessible: `curl http://127.0.0.1:7860/`
- Verify `QWEN_API_URL` in `src/config.py` matches your server

### Voice Clone Mode Errors

```
[ERROR] Configuration Error! Voice Clone mode requires a reference audio file.
```

**Solutions:**
- Ensure reference audio path is correct
- Verify the audio file exists and is in WAV format

### No Text Extracted

```
[ERROR] No text extracted from document
```

**Solutions:**
- Verify file isn't corrupted
- Check if document contains selectable text (not just images)
- For image-based PDFs, use OCR first

### Processing Takes Too Long

**Normal behavior:**
- Each chunk takes ~4-5 minutes with 1.7B model
- Processing is sequential to avoid rate limiting
- Large books will take time - be patient!

## Advanced Usage

### Custom Chunking

Modify chunking behavior by editing the `CHUNK_SIZE_WORDS` in `src/config.py`:

```python
CHUNK_SIZE_WORDS = 800  # Smaller chunks for faster processing
CHUNK_SIZE_WORDS = 1500  # Larger chunks for better flow
```

### Logging

Logs are saved to `logs/audiobook_YYYYMMDD.log` with detailed information about:
- Text extraction progress
- Chunk processing status
- API calls and responses
- Errors and warnings

### Batch Processing

```bash
# Add multiple books
cp *.pdf book_to_convert/
cp *.epub book_to_convert/

# Convert all at once
python src/audiobook_converter.py
```

## Performance

- **Processing Speed**: ~4-5 minutes per chunk (1.7B model)
- **Quality**: High-quality audio suitable for audiobooks
- **Memory Usage**: ~2-4GB RAM during processing
- **Storage**: ~1MB per minute of audio (128kbps MP3)

## Support

- **Issues**: [GitHub Issues](https://github.com/aporb/Qwen3-Audiobook-Converter/issues)
- **Documentation**: See main README.md for overview
