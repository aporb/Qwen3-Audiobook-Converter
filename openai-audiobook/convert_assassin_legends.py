#!/usr/bin/env python3
"""
Convert The Assassin Legends PDF to audiobook.
Run with: python convert_assassin_legends.py
"""

import fitz
import re
import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tts_client import TTSClient
from chunker import TokenAwareChunker
from audio_assembler import AudioAssembler, AudioSegment

# Configuration
PDF_PATH = Path(__file__).parent.parent / 'book_to_convert/the-assassin-legends-myths-of-the-ismailis-9780755612284-9781850437055_compress.pdf'
OUTPUT_DIR = Path(__file__).parent / 'audiobooks'
TEMP_DIR = Path(__file__).parent / 'temp'
VOICE = 'coral'
BOOK_NAME = 'The_Assassin_Legends'
COVER_PATH = Path(__file__).parent / 'cover.jpg'

# Create directories
OUTPUT_DIR.mkdir(exist_ok=True)
TEMP_DIR.mkdir(exist_ok=True)

# AI Intro
INTRO_TEXT = "This audiobook is narrated by an AI voice. The Assassin Legends: Myths of the Isma'ilis, by Farhad Daftary. Originally published in 1995."

# Chapter definitions: (id, title, start_page, end_page, custom_text)
CHAPTERS = [
    ('ch00_intro', 'AI Narrator Introduction', None, None, INTRO_TEXT),
    ('ch01_transliteration', 'Note on Transliteration and Abbreviations', 1, 1, None),
    ('ch02_preface', 'Preface', 2, 3, None),
    ('ch03_introduction', 'Introduction', 4, 10, None),
    ('ch04_ismailis_history', 'The Ismailis in History and in Mediaeval Muslim Writings', 11, 51, None),
    ('ch05_european_perceptions', 'Mediaeval European Perceptions of Islam and the Ismailis', 52, 90, None),
    ('ch06_origins_legends', 'Origins and Early Formation of the Legends', 91, 131, None),
    ('ch07_de_sacy_memoir', 'Silvestre de Sacys Memoir on the Assassins', 132, 202, None),
]


def clean_text(text):
    """Clean OCR artifacts and normalize text for TTS."""
    # Fix common OCR issues
    text = re.sub(r"' ~ u r o ~ e a n", 'European', text)
    text = re.sub(r'\s*~\s*', '', text)
    text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = text.replace('Zranica', 'Iranica')
    text = text.replace('lournal', 'Journal')
    text = text.replace('lslam', 'Islam')
    text = text.replace('Zsma', 'Isma')
    text = text.replace('Medimal', 'Mediaeval')
    text = text.replace('Fomation', 'Formation')
    # Normalize whitespace for TTS
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def extract_chapter_text(doc, start_page, end_page):
    """Extract and clean text from PDF pages."""
    chapter_parts = []
    for page_num in range(start_page - 1, end_page):
        page_text = doc[page_num].get_text('text')
        lines = page_text.split('\n')
        cleaned = []
        for line in lines:
            # Skip running headers
            if 'The Assassin Legend' in line and len(line.strip()) < 30:
                continue
            # Skip page numbers
            if line.strip().isdigit():
                continue
            cleaned.append(line)
        chapter_parts.append('\n'.join(cleaned))
    return '\n\n'.join(chapter_parts)


def log(msg):
    """Print timestamped log message."""
    timestamp = datetime.now().strftime('%H:%M:%S')
    print(f'[{timestamp}] {msg}')
    sys.stdout.flush()


def main():
    log('=' * 60)
    log('AUDIOBOOK CONVERSION')
    log('The Assassin Legends: Myths of the Ismailis')
    log('=' * 60)
    log('')

    # Check for existing progress
    progress_file = TEMP_DIR / 'progress.txt'
    completed_chapters = set()
    if progress_file.exists():
        with open(progress_file) as f:
            completed_chapters = set(line.strip() for line in f if line.strip())
        log(f'Resuming - {len(completed_chapters)} chapters already done')

    # Initialize components
    log('[1/4] Initializing...')
    doc = fitz.open(str(PDF_PATH))
    tts_client = TTSClient(
        voice=VOICE,
        instructions='Read this scholarly historical text with a clear, measured pace. Pronounce Arabic and Persian names carefully.'
    )
    chunker = TokenAwareChunker(max_tokens=1500)
    assembler = AudioAssembler(TEMP_DIR)

    # Process chapters
    log('[2/4] Generating audio for chapters...')
    log('')

    chapter_audio_files = []
    chapter_titles = []

    for ch_id, title, start_page, end_page, custom_text in CHAPTERS:
        chapter_mp3 = TEMP_DIR / f'{ch_id}.mp3'

        # Check if already completed
        if ch_id in completed_chapters and chapter_mp3.exists():
            log(f'  Skipping (cached): {title[:50]}')
            chapter_audio_files.append(str(chapter_mp3))
            chapter_titles.append(title)
            continue

        log(f'  Processing: {title[:50]}...')

        # Get text
        if custom_text:
            text = custom_text
        else:
            text = extract_chapter_text(doc, start_page, end_page)

        text = clean_text(text)
        words = len(text.split())
        log(f'    Words: {words:,}')

        # Chunk the text
        chunks = chunker.chunk_text(text)
        log(f'    Chunks: {len(chunks)}')

        # Generate audio for each chunk
        chunk_files = []
        for i, chunk in enumerate(chunks):
            chunk_path = TEMP_DIR / f'{ch_id}_chunk_{i:04d}.mp3'

            # Skip if chunk already exists
            if chunk_path.exists():
                chunk_files.append(str(chunk_path))
                continue

            log(f'    Generating chunk {i+1}/{len(chunks)}...')
            success = tts_client.generate_speech(chunk, chunk_path)
            if success:
                chunk_files.append(str(chunk_path))
            else:
                log(f'    [!] Failed chunk {i+1}, retrying...')
                time.sleep(5)
                success = tts_client.generate_speech(chunk, chunk_path)
                if success:
                    chunk_files.append(str(chunk_path))
                else:
                    log(f'    [!] Failed chunk {i+1} permanently')

        if chunk_files:
            # Concatenate chunks into chapter
            log(f'    Concatenating {len(chunk_files)} chunks...')
            if assembler.concatenate_audio(chunk_files, str(chapter_mp3)):
                chapter_audio_files.append(str(chapter_mp3))
                chapter_titles.append(title)

                # Mark as completed
                with open(progress_file, 'a') as f:
                    f.write(f'{ch_id}\n')

                # Cleanup chunk files
                for f in chunk_files:
                    Path(f).unlink(missing_ok=True)

                log(f'    Done: {chapter_mp3.name}')
        log('')

    doc.close()

    log(f'[3/4] Assembling audiobook ({len(chapter_audio_files)} chapters)...')

    # Build segments
    segments = []
    for i, (audio_file, title) in enumerate(zip(chapter_audio_files, chapter_titles)):
        segments.append(AudioSegment(
            path=audio_file,
            chapter_id=f'ch{i:02d}',
            chapter_title=title
        ))

    # Create M4B
    output_path = OUTPUT_DIR / f'{BOOK_NAME}_{VOICE}.m4b'
    metadata = {
        'title': "The Assassin Legends: Myths of the Isma'ilis",
        'artist': 'Farhad Daftary',
        'author': 'Farhad Daftary',
        'album': "The Assassin Legends: Myths of the Isma'ilis",
        'album_artist': 'Farhad Daftary',
        'genre': 'Audiobook',
        'year': '1995',
        'comment': 'Narrated by AI voice. Originally published 1995 by I.B. Tauris.'
    }

    # Use cover if available
    cover = str(COVER_PATH) if COVER_PATH.exists() else None
    if cover:
        log(f'Using cover: {COVER_PATH}')

    success = assembler.create_m4b(segments, str(output_path), metadata, cover, '128k')

    if success:
        log('')
        log('[4/4] Cleanup...')

        # Remove progress file
        progress_file.unlink(missing_ok=True)

        log('')
        log('=' * 60)
        log('CONVERSION COMPLETE')
        log('=' * 60)
        log(f'Output: {output_path}')
        log(f'Size: {output_path.stat().st_size / (1024*1024):.1f} MB')
        log('=' * 60)
    else:
        log('[!] Failed to create M4B')
        sys.exit(1)


if __name__ == '__main__':
    main()
