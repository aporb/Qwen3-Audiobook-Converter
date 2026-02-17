# TTS Reader

A lightweight Go CLI tool for converting text files to speech using OpenAI's TTS API.

## Overview

TTS Reader is a simple, fast command-line tool that converts text documents to audio files using OpenAI's GPT-4o-mini-tts model. Perfect for quick conversions without complex setup.

## Features

- ⚡ **Fast & Lightweight**: Written in Go for optimal performance
- 🎯 **Simple Interface**: Interactive prompts or command-line flags
- 📄 **Multiple Formats**: Supports TXT, MD, DOCX, and PDF
- 🎤 **Voice Selection**: Interactive voice picker with 13 voices
- 💬 **Custom Instructions**: Personalized speech style instructions
- 🔧 **Flexible Output**: Configurable output directory

## Installation

### Prerequisites

- Go 1.21 or higher
- OpenAI API key

### Build

```bash
cd tts-reader
go build -o tts-reader
```

## Usage

### Interactive Mode

```bash
./tts-reader
```

This will:
1. Show a file picker with supported files in the current directory
2. Let you choose from 13 available voices
3. Prompt for speech style instructions
4. Convert and save the audio

### Direct Conversion

```bash
# Convert a specific file
./tts-reader document.pdf

# With specific voice
./tts-reader --voice coral notes.md

# With custom instructions
./tts-reader --voice coral --instructions "Read with enthusiasm" report.docx

# Custom output directory
./tts-reader --output-dir ~/Audiobooks book.txt
```

### Available Voices

| Voice | Description |
|-------|-------------|
| `alloy` | Balanced, expressive |
| `ash` | Soft, warm |
| `ballad` | Melodic, engaging |
| `coral` | Warm, narrative (recommended) |
| `echo` | Clear, neutral male |
| `fable` | Storytelling-focused |
| `nova` | Friendly female |
| `onyx` | Deep, authoritative (recommended) |
| `sage` | Wise, measured |
| `shimmer` | Soft, gentle female |
| `verse` | Poetic, flowing |
| `marin` | Calm, professional (recommended) |
| `cedar` | Natural, balanced (recommended) |

**Recommended for audiobooks:** `coral`, `onyx`, `marin`, `cedar`

## Configuration

### Environment Variables

```bash
export OPENAI_API_KEY="your-api-key-here"
```

### Command-Line Flags

| Flag | Description | Default |
|------|-------------|---------|
| `--file` | Path to input file | Interactive picker |
| `--voice` | TTS voice to use | Interactive prompt |
| `--instructions` | Speech style instructions | "Read naturally with clear enunciation" |
| `--output-dir` | Output directory for audio | `audio_output` |

## Examples

```bash
# Convert current directory's files interactively
./tts-reader

# Convert specific PDF with recommended voice
./tts-reader --voice cedar research_paper.pdf

# Convert markdown with custom style
./tts-reader --voice coral --instructions "Read like a documentary narrator" article.md

# Batch-like conversion (run multiple times)
for file in *.txt; do
    ./tts-reader --voice onyx "$file"
done
```

## Project Structure

```
tts-reader/
├── README.md       # This file
├── main.go         # Entry point and CLI
├── extract.go      # Text extraction (TXT, PDF, DOCX)
├── tts.go          # OpenAI TTS API client
├── scanner.go      # File scanning utilities
├── go.mod          # Go module definition
└── go.sum          # Go dependencies
```

## Dependencies

- `github.com/manifoldco/promptui` - Interactive prompts
- Standard library for HTTP requests and file handling

## Troubleshooting

### "OPENAI_API_KEY environment variable is not set"

```bash
export OPENAI_API_KEY="sk-..."
```

### "No supported files found"

Ensure you're in a directory with `.txt`, `.md`, `.docx`, or `.pdf` files, or specify a file path:

```bash
./tts-reader /path/to/your/file.txt
```

### "Conversion failed"

- Check your internet connection
- Verify your OpenAI API key is valid
- Ensure you have API credits

## Cost

OpenAI TTS pricing: ~$0.015 per 1,000 characters

Example costs:
- 10-page document: ~$0.05
- 100-page book: ~$1.50

## License

MIT License - See parent project for details.
