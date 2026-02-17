# OpenAI Audiobook Converter - Development Tasks

## Project Status: Testing

Last Updated: 2026-01-26

## Completed Tasks

- [x] Create project structure and directories
- [x] Set up requirements.txt
- [x] Write initial README.md
- [x] Implement EPUB parser module (epub_parser.py)
- [x] Implement token-aware text chunker (chunker.py)
- [x] Implement OpenAI TTS client (tts_client.py)
- [x] Implement audio assembler (audio_assembler.py)
- [x] Implement cost estimator (cost_estimator.py)
- [x] Implement progress tracking (progress.py)
- [x] Implement main converter (convert.py)

## In Progress

- [ ] Test end-to-end with The Ismaili Assassins EPUB
- [ ] Verify M4B chapter markers work correctly
- [ ] Finalize documentation

## Pending

- [ ] Add unit tests
- [ ] Performance optimization (if needed)

## Architecture Overview

```
convert.py (orchestrator)
    │
    ├── epub_parser.py     → Extract text & chapters from EPUB
    ├── chunker.py         → Split text into token-safe chunks
    ├── cost_estimator.py  → Calculate API costs
    ├── tts_client.py      → Call OpenAI TTS API
    ├── audio_assembler.py → Combine chunks → M4B
    └── progress.py        → Checkpoint/resume management
```

## Configuration Flow

```
Parent YAML Config (chapters.yaml / voicedesign_*.yaml)
    │
    ├── voice.instruct → OpenAI instructions parameter
    ├── chapters.include/exclude → Chapter filtering
    ├── intro_text/outro_text → Special audio sections
    └── conversion settings → Pause durations, etc.
```

## Key Decisions

1. **Voice**: `coral` (warm, engaging - good for narrative)
2. **Format**: M4B with chapter markers
3. **Chunking**: Sentence-aware, ~3000 tokens max (under 4096 limit)
4. **Processing**: Batch (simpler than streaming)
5. **Cost Display**: Show estimates before conversion

## File Summary

| File | Lines | Purpose |
|------|-------|---------|
| convert.py | ~400 | Main entry point and orchestrator |
| epub_parser.py | ~300 | EPUB parsing with chapter discovery |
| chunker.py | ~180 | Token-aware text splitting |
| tts_client.py | ~180 | OpenAI TTS API wrapper |
| audio_assembler.py | ~280 | FFmpeg-based M4B creation |
| cost_estimator.py | ~150 | API cost calculation |
| progress.py | ~150 | Checkpoint/resume management |
