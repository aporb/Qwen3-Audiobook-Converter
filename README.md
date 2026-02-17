# 🎧 Audiobook Converter Suite

A comprehensive collection of audiobook conversion tools supporting multiple TTS engines, formats, and deployment options.

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Go](https://img.shields.io/badge/Go-1.21+-00ADD8.svg)](https://golang.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📚 Overview

This repository contains **4 distinct applications** for converting text to audiobooks:

| Application | Language | TTS Engine | Best For |
|------------|----------|------------|----------|
| **Qwen3 TTS Converter** | Python | Qwen3 TTS (Local) | High-quality local voice synthesis |
| **OpenAI Audiobook** | Python | OpenAI GPT-4o-mini | Cloud-based with chapter detection |
| **TTS Reader** | Go | OpenAI TTS | Simple CLI conversions |
| **VoxCraft** | Python/JS | MLX TTS | Full-stack web interface |

## 🚀 Quick Start

Choose your tool based on your needs:

### 🎯 For Local High-Quality TTS (Qwen3)
```bash
# Install dependencies
pip install -r requirements.txt

# Place your book in book_to_convert/
cp your_book.pdf book_to_convert/

# Run the converter
python src/audiobook_converter.py
```
**Output:** `audiobooks/your_book.mp3`

[→ Full Documentation](docs/QWEN3_GUIDE.md)

### ☁️ For Cloud-Based with Chapters (OpenAI)
```bash
cd openai-audiobook
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Convert with chapter detection
python convert.py --epub ../book_to_convert/book.epub --config ../chapters.yaml
```
**Output:** M4B with embedded chapters and cover art

[→ Full Documentation](openai-audiobook/README.md)

### ⚡ For Simple CLI Conversions
```bash
cd tts-reader
# Build first: go build -o tts-reader

# Interactive mode
./tts-reader

# Or direct conversion
./tts-reader --voice coral --instructions "Read clearly" document.pdf
```

[→ Full Documentation](tts-reader/README.md)

### 🌐 For Web Interface
```bash
cd voxcraft
docker-compose up
# Open http://localhost:3000
```

[→ Full Documentation](voxcraft/README.md)

## 📁 Repository Structure

```
Qwen3-Audiobook-Converter/
├── README.md                 # This file
├── LICENSE                   # MIT License
├── requirements.txt          # Main Python dependencies
├── .gitignore               # Git ignore rules
│
├── 📄 docs/                 # Documentation
│   ├── QUICKSTART.md        # Quick start guide
│   ├── QWEN3_GUIDE.md       # Qwen3 converter docs
│   └── QWEN3_GUIDE.md       # Qwen3 converter guide
│
├── ⚙️  config/              # Configuration files
│   ├── chapters.yaml        # Chapter definitions
│   ├── config_schema.yaml   # Config validation schema
│   └── voicedesign_*.yaml   # Voice design configs
│
├── 🐍 src/                  # Main Qwen3 converter source
│   ├── audiobook_converter.py    # Main converter
│   ├── mlx_tts_engine.py         # MLX TTS implementation
│   ├── convert_audiobook.py      # Legacy converter
│   └── config.py                 # Configuration module
│
├── 📓 notebooks/            # Jupyter notebooks
│   └── Qwen3_TTS_Audiobook_Converter.ipynb
│
├── 📂 book_to_convert/      # Input folder
│   └── input_here.txt
│
├── 🎧 audiobooks/           # Output folder
│   └── output_here.txt
│
├── 💾 cache/                # Audio cache
├── 🧩 chunks/               # Temporary chunks
├── 📊 logs/                 # Processing logs
│
├── 🔧 openai-audiobook/     # OpenAI TTS converter
│   ├── README.md
│   ├── convert.py
│   ├── epub_parser.py
│   └── ...
│
├── ⚡ tts-reader/            # Go CLI tool
│   ├── README.md
│   ├── main.go
│   └── ...
│
└── 🌐 voxcraft/             # Full-stack web app
    ├── README.md
    ├── docker-compose.yml
    ├── frontend/
    └── backend/
```

## 🎨 Features Comparison

| Feature | Qwen3 | OpenAI | TTS-Reader | VoxCraft |
|---------|-------|---------|------------|----------|
| **Local Processing** | ✅ Yes | ❌ No | ❌ No | ✅ Yes |
| **Chapter Detection** | ❌ No | ✅ Yes | ❌ No | ✅ Yes |
| **Voice Cloning** | ✅ Yes | ✅ Yes | ✅ Yes | ✅ Yes |
| **Web Interface** | ❌ No | ❌ No | ❌ No | ✅ Yes |
| **Multiple Formats** | ✅ All | ✅ EPUB | ✅ TXT/PDF/DOCX | ✅ All |
| **M4B Output** | ❌ No | ✅ Yes | ❌ No | ❌ No |
| **Resume Capability** | ✅ Yes | ✅ Yes | ❌ No | ✅ Yes |
| **Cost** | Free (local) | ~$0.015/1K chars | ~$0.015/1K chars | Free (local) |

## 📋 Requirements

### System Requirements
- **Python**: 3.8+ (for Python tools)
- **Go**: 1.21+ (for tts-reader)
- **Docker**: Latest (for VoxCraft)
- **FFmpeg**: Required for audio processing
- **RAM**: 4GB+ recommended
- **Storage**: ~100MB per hour of audiobook

### Installing FFmpeg
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg`
- **Windows**: Download from [ffmpeg.org](https://ffmpeg.org/download.html)

## 🎯 Supported Formats

| Format | Qwen3 | OpenAI | TTS-Reader | VoxCraft |
|--------|-------|---------|------------|----------|
| TXT | ✅ | ✅ | ✅ | ✅ |
| PDF | ✅ | ❌ | ✅ | ✅ |
| EPUB | ✅ | ✅ | ❌ | ✅ |
| DOCX | ✅ | ❌ | ✅ | ✅ |
| DOC | ✅ | ❌ | ❌ | ✅ |

## 🛠️ Configuration

Each application has its own configuration:

- **Qwen3**: Edit `config.py` or use command-line flags
- **OpenAI**: YAML configs in `config/` directory
- **TTS-Reader**: Command-line flags
- **VoxCraft**: Environment variables in docker-compose.yml

## 🐛 Troubleshooting

### Common Issues

**Qwen API Connection Failed**
```
Ensure Qwen Gradio server is running on http://127.0.0.1:7860
```

**FFmpeg Not Found**
```bash
# macOS
brew install ffmpeg

# Linux
sudo apt-get install ffmpeg
```

**OpenAI Rate Limits**
```
The OpenAI converter includes automatic retry with exponential backoff.
```

See individual application READMEs for detailed troubleshooting.

## 🤝 Contributing

Contributions are welcome! Each application has its own structure:

1. **Fork** the repository
2. **Create** your feature branch
3. **Commit** your changes
4. **Push** to the branch
5. **Open** a Pull Request

Please ensure your code follows the existing style and includes appropriate tests.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **[Qwen TTS](https://github.com/QwenLM/Qwen3-TTS)** - Open-source voice synthesis
- **[OpenAI TTS](https://platform.openai.com/docs/guides/text-to-speech)** - Cloud TTS API
- **[MLX](https://github.com/ml-explore/mlx)** - Apple Silicon ML framework
- All contributors and users

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/WhiskeyCoder/Qwen3-Audiobook-Converter/issues)
- **Discussions**: Open a discussion on GitHub

---

**Made with ❤️ for the audiobook community**
