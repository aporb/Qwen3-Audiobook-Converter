#!/usr/bin/env python3
"""
Re-assemble the audiobook with cover art.
Run after convert_assassin_legends.py completes.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from audio_assembler import AudioAssembler, AudioSegment

TEMP_DIR = Path(__file__).parent / 'temp'
OUTPUT_DIR = Path(__file__).parent / 'audiobooks'
COVER_PATH = Path(__file__).parent / 'cover.jpg'

# Chapter files in order
CHAPTERS = [
    ('ch00_intro.mp3', 'AI Narrator Introduction'),
    ('ch01_transliteration.mp3', 'Note on Transliteration and Abbreviations'),
    ('ch02_preface.mp3', 'Preface'),
    ('ch03_introduction.mp3', 'Introduction'),
    ('ch04_ismailis_history.mp3', 'The Ismailis in History and in Mediaeval Muslim Writings'),
    ('ch05_european_perceptions.mp3', 'Mediaeval European Perceptions of Islam and the Ismailis'),
    ('ch06_origins_legends.mp3', 'Origins and Early Formation of the Legends'),
    ('ch07_de_sacy_memoir.mp3', "Silvestre de Sacy's Memoir on the Assassins"),
]

def main():
    print('Assembling audiobook with cover...')

    # Check all chapter files exist
    segments = []
    for i, (filename, title) in enumerate(CHAPTERS):
        filepath = TEMP_DIR / filename
        if not filepath.exists():
            print(f'[!] Missing: {filepath}')
            sys.exit(1)
        segments.append(AudioSegment(
            path=str(filepath),
            chapter_id=f'ch{i:02d}',
            chapter_title=title
        ))

    print(f'Found {len(segments)} chapters')

    # Check cover
    if not COVER_PATH.exists():
        print(f'[!] Cover not found: {COVER_PATH}')
        sys.exit(1)
    print(f'Using cover: {COVER_PATH}')

    # Assemble
    assembler = AudioAssembler(TEMP_DIR)
    output_path = OUTPUT_DIR / 'The_Assassin_Legends_coral.m4b'

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

    success = assembler.create_m4b(
        segments,
        str(output_path),
        metadata,
        str(COVER_PATH),  # Cover art!
        '128k'
    )

    if success:
        print()
        print('=' * 50)
        print('DONE!')
        print('=' * 50)
        print(f'Output: {output_path}')
        print(f'Size: {output_path.stat().st_size / (1024*1024):.1f} MB')
    else:
        print('[!] Failed to create M4B')
        sys.exit(1)

if __name__ == '__main__':
    main()
