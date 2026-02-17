# Contributing to Audiobook Converter Suite

Thank you for your interest in contributing! This document provides guidelines for contributing to all 4 applications in this suite.

## 🎯 Quick Links

- [Qwen3 TTS Converter](#qwen3-tts-converter)
- [OpenAI Audiobook](#openai-audiobook)
- [TTS Reader](#tts-reader)
- [VoxCraft](#voxcraft)

## 🤝 How to Contribute

### Reporting Issues

1. **Check existing issues** first to avoid duplicates
2. **Use the appropriate template** when creating new issues
3. **Provide detailed information**:
   - Application name (Qwen3/OpenAI/TTS-Reader/VoxCraft)
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python/Go version, etc.)

### Suggesting Features

1. Open a **Feature Request** issue
2. Describe the use case and expected behavior
3. Explain why it would benefit users

### Code Contributions

#### General Workflow

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Make** your changes
4. **Test** thoroughly (see testing sections below)
5. **Commit** with clear messages (see [Commit Guidelines](#commit-guidelines))
6. **Push** to your fork
7. **Open** a Pull Request

#### Commit Guidelines

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Test additions/changes
- `chore`: Build process, dependencies, etc.

**Scopes:**
- `qwen3`: Qwen3 TTS Converter
- `openai`: OpenAI Audiobook
- `tts-reader`: TTS Reader (Go)
- `voxcraft`: VoxCraft web app
- `docs`: Documentation

**Examples:**
```
feat(qwen3): add support for DOC format
fix(voxcraft): resolve SSE connection drop
docs: update installation instructions
refactor(openai): simplify chapter detection logic
```

---

## 🐍 Qwen3 TTS Converter

### Development Setup

```bash
# Clone and navigate
 git clone https://github.com/aporb/Qwen3-Audiobook-Converter.git
cd Qwen3-Audiobook-Converter

# Install dependencies
pip install -r requirements.txt

# Install FFmpeg
# macOS: brew install ffmpeg
# Linux: sudo apt-get install ffmpeg
```

### Code Structure

```
src/
├── audiobook_converter.py    # Main entry point
├── config.py                 # Configuration management
├── mlx_tts_engine.py         # MLX TTS implementation
└── __init__.py
```

### Testing

- Test with various document formats (PDF, EPUB, DOCX, TXT)
- Verify voice modes work (custom_voice, voice_clone, voice_design)
- Check caching behavior
- Test error handling and retries

### Code Style

- Follow PEP 8
- Use type hints where appropriate
- Add docstrings for functions
- Keep functions focused and modular

---

## ☁️ OpenAI Audiobook

### Development Setup

```bash
cd openai-audiobook
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Code Structure

```
openai-audiobook/
├── convert.py           # Main converter
├── epub_parser.py       # EPUB parsing
├── chapter_detector.py  # Chapter detection
└── audio_generator.py   # Audio generation
```

### Testing

- Test with various EPUB structures
- Verify chapter detection accuracy
- Check M4B output with embedded metadata
- Test cost estimation accuracy

### Environment Variables

Create a `.env` file:
```
OPENAI_API_KEY=your_key_here
```

---

## ⚡ TTS Reader

### Development Setup

```bash
cd tts-reader

# Install Go 1.21+
# https://golang.org/doc/install

# Build
go build -o tts-reader

# Run
./tts-reader --help
```

### Code Structure

```
tts-reader/
├── main.go              # Entry point
├── cmd/                 # Command handling
├── internal/
│   ├── converter/       # TTS conversion logic
│   └── parser/          # Document parsing
└── go.mod
```

### Testing

```bash
# Run tests
go test ./...

# Test specific features
go test -v ./internal/converter
```

### Code Style

- Follow standard Go conventions
- Use `gofmt` for formatting
- Keep packages small and focused
- Write clear error messages

---

## 🌐 VoxCraft

### Development Setup

```bash
cd voxcraft

# Backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# Frontend
cd frontend
npm install
```

### Running Development Server

```bash
# Use the provided script
./start-dev.sh

# Or manually:
# Terminal 1: Backend
cd backend
python main.py

# Terminal 2: Frontend
cd frontend
npm run dev
```

### Code Structure

```
voxcraft/
├── backend/
│   ├── main.py
│   ├── routers/         # API endpoints
│   ├── services/        # Business logic
│   ├── models/          # Database models
│   └── tasks/           # Background tasks
└── frontend/
    ├── src/
    │   ├── components/  # React components
    │   ├── stores/      # Zustand stores
    │   └── lib/         # Utilities
    └── package.json
```

### Frontend Guidelines

- Use TypeScript for all new code
- Follow existing component patterns
- Use Tailwind CSS for styling
- Keep components small and reusable
- Use Zustand for state management

### Backend Guidelines

- Use FastAPI patterns
- Add proper type hints
- Document API endpoints
- Handle errors gracefully
- Use SQLAlchemy for database operations

### Testing

```bash
# Frontend
cd frontend
npm run test

# Backend
cd backend
pytest
```

---

## 📋 Pull Request Checklist

Before submitting a PR, ensure:

- [ ] Code follows style guidelines for the specific application
- [ ] Changes are tested locally
- [ ] Documentation is updated (if needed)
- [ ] Commit messages follow conventions
- [ ] No breaking changes (or clearly documented)
- [ ] PR description explains the changes

## 🏷️ Release Process

1. Version bumps follow [Semantic Versioning](https://semver.org/)
2. Update CHANGELOG.md with changes
3. Create a git tag: `git tag -a v1.2.3 -m "Release v1.2.3"`
4. Push tags: `git push origin --tags`

## 💬 Communication

- Be respectful and constructive
- Ask questions in issues if unclear
- Provide context in discussions
- Help review other PRs

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to the Audiobook Converter Suite!** 🎧
