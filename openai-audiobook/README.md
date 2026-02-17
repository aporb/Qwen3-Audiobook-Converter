# OpenAI Audiobook Converter

Convert EPUB books to audiobooks using OpenAI's GPT-4o-mini TTS API.

## Features

- **OpenAI TTS Integration**: Uses `gpt-4o-mini-tts` model with voice customization
- **Chapter-aware Processing**: Preserves book structure with chapter markers
- **M4B Output**: Creates audiobook files with embedded chapters and cover art
- **Cost Estimation**: Shows estimated API costs before conversion
- **Resume Capability**: Checkpoint system allows resuming interrupted conversions
- **Config Compatibility**: Reuses YAML configs from the parent Qwen3-TTS project

## Quick Start

### 1. Set up virtual environment

```bash
cd openai-audiobook
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Ensure OpenAI API key is set

```bash
# Should already be in ~/.zshrc
export OPENAI_API_KEY="your-api-key"
```

### 3. Run conversion

```bash
# With existing YAML config from parent project
python convert.py --epub ../book_to_convert/The_Ismaili_Assassins_A_History_of_Medieval_Murder.epub \
                  --config ../voicedesign_american_male.yaml

# Dry run to see cost estimate
python convert.py --epub ../book_to_convert/book.epub --config ../chapters.yaml --dry-run

# With custom voice and instructions
python convert.py --epub ../book_to_convert/book.epub \
                  --voice coral \
                  --instructions "Speak in a calm, authoritative tone suitable for historical non-fiction."
```

## Configuration

### Using Parent Project YAML Configs

This converter is designed to work with YAML configurations from the parent Qwen3-TTS project:

```yaml
# voicedesign_american_male.yaml
intro_text: "This audiobook is read by A I."
title_announcement: "Book Title, by Author Name."
outro_text: "Thank you for listening."

voice:
  slug: american_male
  language: English
  instruct: >
    Adult American male, professional audiobook narrator.
    Clear enunciation, calm and authoritative tone.

chapters:
  include:
    - foreword
    - introduction
    - chapter01
  exclude:
    - frontcoverImage
    - copyrightPage

conversion:
  announce_chapters: true
  chapter_pause: 2.5
```

### OpenAI-Specific Settings

Create `openai_config.yaml` to customize OpenAI TTS settings:

```yaml
# OpenAI TTS Configuration
openai:
  model: gpt-4o-mini-tts
  voice: coral  # alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse
  response_format: mp3

output:
  format: m4b
  bitrate: 128k
  embed_cover: true
```

## Available Voices

| Voice | Description |
|-------|-------------|
| `coral` | Warm, engaging. Great for narrative content |
| `onyx` | Deep, authoritative male voice |
| `echo` | Clear, neutral male voice |
| `alloy` | Balanced, expressive |
| `nova` | Friendly female voice |
| `shimmer` | Soft, gentle female voice |
| `fable` | Storytelling-focused |
| `sage` | Wise, measured tone |

**Recommended for audiobooks**: `coral`, `onyx`, or `echo`

## Cost Estimation

OpenAI TTS pricing (as of 2025):
- `gpt-4o-mini-tts`: ~$0.015 per 1,000 characters

The converter displays cost estimates before starting:

```
=== Cost Estimate ===
Total characters: 450,000
Estimated cost: $6.75 USD

Breakdown by chapter:
  foreword:     12,500 chars ($0.19)
  introduction: 28,000 chars ($0.42)
  chapter01:    45,000 chars ($0.68)
  ...

Proceed with conversion? [y/N]
```

## Output Structure

```
openai-audiobook/
├── audiobooks/           # Final M4B output
│   └── Book_Name.m4b
├── cache/                # Cached audio chunks
│   └── {hash}.mp3
├── temp/                 # Temporary chapter files
│   └── chapter01.mp3
├── logs/                 # Processing logs
│   └── conversion_20260126.log
└── .progress.json        # Resume checkpoint
```

## API Reference

### Main Modules

| Module | Purpose |
|--------|---------|
| `convert.py` | Main entry point and orchestrator |
| `epub_parser.py` | EPUB text extraction and chapter discovery |
| `chunker.py` | Token-aware text splitting |
| `tts_client.py` | OpenAI TTS API wrapper |
| `audio_assembler.py` | Combine chunks into M4B |
| `cost_estimator.py` | Calculate conversion costs |
| `progress.py` | Checkpoint/resume management |

## Requirements

- Python 3.9+
- FFmpeg (for M4B creation)
- OpenAI API key with TTS access

## Troubleshooting

### "Rate limit exceeded"
The converter includes automatic retry with exponential backoff. For very long books, consider:
- Running during off-peak hours
- Using a higher tier API key

### "FFmpeg not found"
Install FFmpeg:
```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg
```

### Resume a failed conversion
Just run the same command again - the converter will detect the progress file and resume from the last completed chapter.

## License

MIT License - See parent project for details.
