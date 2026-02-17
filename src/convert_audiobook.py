#!/usr/bin/env python3
"""
Qwen3-TTS Audiobook Converter - Local Script
============================================
Converts EPUB/PDF/TXT to voice-cloned audiobooks with chapter markers.

Optimized for Apple Silicon (M4 Pro) with:
- Memory management (MPS cache clearing)
- Checkpoint/resume support
- Automatic chunk retry with smaller splits
- Graceful shutdown handling

Usage:
    python convert_audiobook.py --epub book.epub --voice sample.wav
    python convert_audiobook.py --epub book.epub --voice sample.wav --config chapters.yaml
    python convert_audiobook.py --epub book.epub --voice sample.wav --dry-run
"""

import argparse
import gc
import json
import os
import re
import signal
import subprocess
import sys
import time
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import psutil
import soundfile as sf
import torch
import whisper
import yaml
from pydub import AudioSegment
from qwen_tts import Qwen3TTSModel
from tqdm import tqdm

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False


# ============================================================
# CONSTANTS
# ============================================================

DEFAULT_CONFIG = {
    'intro_text': None,
    'title_announcement': None,
    'outro_text': None,
    'chapters': {
        'include': None,
        'exclude': [
            'frontcoverImage', 'title', 'copyrightPage', 'contents',
            'notes', 'bibliography', 'index', 'maps', 'timeline'
        ]
    },
    'conversion': {
        'announce_chapters': True,
        'chapter_pause': 2.5,
        'chunk_size': 1500,
        'min_chunk_size': 200,
        'max_retries': 3,
        'retry_delay': 5
    },
    'text_cleaning': {
        'fix_spaced_capitals': True,
        'remove_footnotes': True,
        'normalize_special_chars': True
    },
    'output': {
        'format': 'm4b',
        'bitrate': '128k',
        'embed_cover': True
    },
    'memory': {
        'clear_cache_per_chapter': True,
        'low_memory_threshold': 4.0,
        'emergency_split_threshold': 2.0
    }
}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dictionaries. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class Chapter:
    """Represents a chapter with its content and metadata."""
    id: str
    title: str
    file_path: str
    content: str
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.content.split())


@dataclass
class ChapterAudio:
    """Audio data for a single chapter."""
    id: str
    title: str
    audio_path: str
    sample_rate: int
    start_time: float = 0.0
    duration: float = 0.0


@dataclass
class ConversionState:
    """Tracks conversion progress for resume capability."""
    epub_path: str
    voice_path: str
    output_path: str
    config_path: Optional[str]
    chapters_total: int = 0
    chapters_completed: List[str] = field(default_factory=list)
    chapter_audio_files: Dict[str, str] = field(default_factory=dict)
    started_at: str = ""
    updated_at: str = ""
    completed: bool = False

    def save(self, path: Path):
        """Save state to JSON file."""
        self.updated_at = datetime.now().isoformat()
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'ConversionState':
        """Load state from JSON file."""
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)


# ============================================================
# EPUB PARSER
# ============================================================

class EPUBParser:
    """Parse EPUB files using OPF spine for reading order and NCX for chapter titles."""

    NS = {
        'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'opf': 'http://www.idpf.org/2007/opf',
        'dc': 'http://purl.org/dc/elements/1.1/',
        'ncx': 'http://www.daisy.org/z3986/2005/ncx/'
    }

    def __init__(self, epub_path: str):
        self.epub_path = epub_path
        self.opf_path = None
        self.opf_dir = None
        self.metadata = {}
        self.manifest = {}
        self.spine = []
        self.ncx_chapters = {}
        self.cover_path = None

    def parse(self) -> 'EPUBParser':
        """Parse the EPUB file."""
        with zipfile.ZipFile(self.epub_path, 'r') as z:
            self._find_opf(z)
            self._parse_opf(z)
            self._parse_ncx(z)
            self._find_cover(z)
        return self

    def _find_opf(self, z: zipfile.ZipFile):
        """Find OPF file location from container.xml."""
        container = z.read('META-INF/container.xml').decode('utf-8')
        root = ET.fromstring(container)
        rootfile = root.find('.//container:rootfile', self.NS)
        self.opf_path = rootfile.get('full-path')
        self.opf_dir = str(Path(self.opf_path).parent)
        if self.opf_dir == '.':
            self.opf_dir = ''

    def _parse_opf(self, z: zipfile.ZipFile):
        """Parse OPF for metadata, manifest, and spine."""
        opf_content = z.read(self.opf_path).decode('utf-8')
        root = ET.fromstring(opf_content)

        # Metadata
        metadata = root.find('opf:metadata', self.NS)
        if metadata is not None:
            title = metadata.find('dc:title', self.NS)
            creator = metadata.find('dc:creator', self.NS)
            self.metadata['title'] = title.text if title is not None else 'Unknown'
            self.metadata['author'] = creator.text if creator is not None else 'Unknown'

            for meta in metadata.findall('opf:meta', self.NS):
                if meta.get('name') == 'cover':
                    self.metadata['cover_id'] = meta.get('content')

        # Manifest
        manifest = root.find('opf:manifest', self.NS)
        for item in manifest.findall('opf:item', self.NS):
            item_id = item.get('id')
            self.manifest[item_id] = {
                'href': item.get('href'),
                'media_type': item.get('media-type')
            }

        # Spine (reading order)
        spine = root.find('opf:spine', self.NS)
        for itemref in spine.findall('opf:itemref', self.NS):
            idref = itemref.get('idref')
            linear = itemref.get('linear', 'yes')
            if linear == 'yes' and idref in self.manifest:
                media_type = self.manifest[idref]['media_type']
                if media_type in ('application/xhtml+xml', 'text/html'):
                    self.spine.append(idref)

    def _parse_ncx(self, z: zipfile.ZipFile):
        """Parse NCX for chapter titles."""
        ncx_id = None
        for item_id, item in self.manifest.items():
            if item['media_type'] == 'application/x-dtbncx+xml':
                ncx_id = item_id
                break

        if not ncx_id:
            return

        ncx_href = self.manifest[ncx_id]['href']
        ncx_path = f"{self.opf_dir}/{ncx_href}" if self.opf_dir else ncx_href

        try:
            ncx_content = z.read(ncx_path).decode('utf-8')
            root = ET.fromstring(ncx_content)

            for navpoint in root.findall('.//ncx:navPoint', self.NS):
                label = navpoint.find('ncx:navLabel/ncx:text', self.NS)
                content = navpoint.find('ncx:content', self.NS)

                if label is not None and content is not None:
                    src = content.get('src')
                    file_ref = src.split('#')[0] if src else None
                    title = label.text

                    if file_ref and title:
                        self.ncx_chapters[file_ref] = title
        except Exception:
            pass

    def _find_cover(self, z: zipfile.ZipFile):
        """Find and extract cover image."""
        cover_id = self.metadata.get('cover_id')
        if cover_id and cover_id in self.manifest:
            cover_href = self.manifest[cover_id]['href']
            cover_path = f"{self.opf_dir}/{cover_href}" if self.opf_dir else cover_href

            try:
                cover_data = z.read(cover_path)
                ext = Path(cover_href).suffix
                temp_cover = Path("/tmp") / f"audiobook_cover{ext}"
                with open(temp_cover, 'wb') as f:
                    f.write(cover_data)
                self.cover_path = str(temp_cover)
            except Exception:
                pass

    def get_all_chapter_ids(self) -> List[Tuple[str, str]]:
        """Get all chapter IDs with titles for display."""
        chapters = []
        with zipfile.ZipFile(self.epub_path, 'r') as z:
            for item_id in self.spine:
                item = self.manifest[item_id]
                href = item['href']
                title = self.ncx_chapters.get(href, item_id)
                chapters.append((item_id, title))
        return chapters

    def get_chapters(
        self,
        include_ids: List[str] = None,
        exclude_ids: List[str] = None,
        text_cleaner: callable = None
    ) -> List[Chapter]:
        """Get chapters in reading order with optional filtering."""
        chapters = []

        with zipfile.ZipFile(self.epub_path, 'r') as z:
            for item_id in self.spine:
                if include_ids and item_id not in include_ids:
                    continue
                if exclude_ids and item_id in exclude_ids:
                    continue

                item = self.manifest[item_id]
                href = item['href']
                file_path = f"{self.opf_dir}/{href}" if self.opf_dir else href
                title = self.ncx_chapters.get(href, item_id)

                try:
                    content = z.read(file_path).decode('utf-8', errors='ignore')
                    clean_content = clean_html(content)
                    if text_cleaner:
                        clean_content = text_cleaner(clean_content)

                    if clean_content.strip():
                        chapters.append(Chapter(
                            id=item_id,
                            title=title,
                            file_path=file_path,
                            content=clean_content
                        ))
                except Exception:
                    continue

        return chapters


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_html(html_content: str) -> str:
    """Clean HTML content to plain text."""
    if not html_content:
        return ""

    if BS4_AVAILABLE:
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            for script in soup(["script", "style"]):
                script.decompose()
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            return ' '.join(chunk for chunk in chunks if chunk)
        except Exception:
            pass

    # Fallback
    html_content = re.sub(r'<style[^>]*>.*?</style>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<script[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    html_content = re.sub(r'<[^>]+>', ' ', html_content)
    html_content = unescape(html_content)
    return re.sub(r'\s+', ' ', html_content).strip()


def fix_spaced_capitals(text: str) -> str:
    """Convert 'A H OUSE D IVIDED' to 'A House Divided'."""
    def fix_word(match):
        chars = match.group(0).replace(' ', '')
        if len(chars) >= 2:
            return chars[0] + chars[1:].lower()
        return chars

    pattern = r'\b([A-Z]\s+){2,}[A-Z]+\b'
    return re.sub(pattern, fix_word, text)


def remove_footnote_markers(text: str) -> str:
    """Remove footnote symbols."""
    markers = r'[*\u2020\u2021\u00a7\u00b6\u2016\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u2070]+'
    text = re.sub(r'\s*' + markers + r'\s*', ' ', text)
    return re.sub(r'\s+', ' ', text)


def normalize_special_chars(text: str) -> str:
    """Normalize special characters for better TTS."""
    text = text.replace('\u2014', ' - ')  # em-dash
    text = text.replace('\u2013', ' - ')  # en-dash
    text = text.replace('\u201c', '"').replace('\u201d', '"')  # curly quotes
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2026', '...')  # ellipsis
    return text


def create_text_cleaner(config: dict):
    """Create a text cleaning function based on config."""
    def cleaner(text: str) -> str:
        if config.get('fix_spaced_capitals', True):
            text = fix_spaced_capitals(text)
        if config.get('remove_footnotes', True):
            text = remove_footnote_markers(text)
        if config.get('normalize_special_chars', True):
            text = normalize_special_chars(text)
        return re.sub(r'\s+', ' ', text).strip()
    return cleaner


# ============================================================
# CHUNKING
# ============================================================

def split_into_chunks(text: str, chunk_size_words: int = 1500) -> List[str]:
    """Split text into manageable chunks at sentence boundaries."""
    text = re.sub(r'\s+', ' ', text).strip()
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks, current_chunk, current_words = [], "", 0

    for sentence in sentences:
        sentence_words = len(sentence.split())
        if current_words + sentence_words <= chunk_size_words:
            current_chunk += sentence + " "
            current_words += sentence_words
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + " "
            current_words = sentence_words

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c.strip()]


# ============================================================
# MEMORY MANAGEMENT
# ============================================================

def get_available_memory_gb() -> float:
    """Get available system memory in GB."""
    return psutil.virtual_memory().available / (1024 ** 3)


def clear_mps_cache():
    """Clear MPS memory cache (Apple Silicon)."""
    if hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
        if hasattr(torch.mps, 'empty_cache'):
            torch.mps.empty_cache()
    gc.collect()


def get_device_and_dtype() -> Tuple[str, torch.dtype]:
    """Auto-detect best device and dtype."""
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", torch.float32
    else:
        return "cpu", torch.float32


# ============================================================
# AUDIOBOOK CONVERTER
# ============================================================

class AudiobookConverter:
    """Convert books to audiobooks with chapter markers and M4B output."""

    def __init__(
        self,
        voice_path: str,
        transcript_path: Optional[str] = None,
        config: dict = None,
        output_dir: Path = None
    ):
        self.voice_path = voice_path
        self.transcript_path = transcript_path
        self.config = deep_merge(DEFAULT_CONFIG, config or {})
        self.output_dir = output_dir or Path("audiobooks")
        self.output_dir.mkdir(exist_ok=True)

        # Create temp directory for chapter audio
        self.temp_dir = self.output_dir / ".temp"
        self.temp_dir.mkdir(exist_ok=True)

        self.device, self.dtype = get_device_and_dtype()
        self.tts_model = None
        self.whisper_model = None
        self.ref_text = None
        self.sample_rate = 24000

        # Graceful shutdown
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal gracefully."""
        print("\n[!] Shutdown requested - saving progress...")
        self._shutdown_requested = True

    def load_models(self):
        """Load TTS and Whisper models."""
        print(f"[*] Device: {self.device} ({self.dtype})")
        print(f"[*] Available memory: {get_available_memory_gb():.1f} GB")

        print("[*] Loading Whisper model...")
        self.whisper_model = whisper.load_model("base")
        print("[+] Whisper loaded")

        print("[*] Loading Qwen3-TTS model (~6GB)...")
        self.tts_model = Qwen3TTSModel.from_pretrained(
            "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
            device_map=self.device,
            torch_dtype=self.dtype
        )
        print("[+] Qwen3-TTS loaded")

        # Get reference text
        if self.transcript_path and Path(self.transcript_path).exists():
            with open(self.transcript_path, 'r') as f:
                self.ref_text = f.read().strip()
            print(f"[+] Transcript loaded: {self.ref_text[:80]}...")
        else:
            print("[*] Transcribing voice sample with Whisper...")
            result = self.whisper_model.transcribe(self.voice_path)
            self.ref_text = result["text"].strip()
            print(f"[+] Auto-transcription: {self.ref_text}")

        print(f"[*] Available memory after loading: {get_available_memory_gb():.1f} GB")

    def _generate_audio(self, text: str) -> Tuple[np.ndarray, int]:
        """Generate audio using TTS model."""
        wavs, sr = self.tts_model.generate_voice_clone(
            text=text,
            language="English",
            ref_audio=self.voice_path,
            ref_text=self.ref_text,
            x_vector_only_mode=False,
            non_streaming_mode=True
        )
        self.sample_rate = sr
        return wavs[0], sr

    def _create_silence(self, duration_sec: float) -> np.ndarray:
        """Create silence array."""
        return np.zeros(int(duration_sec * self.sample_rate), dtype=np.float32)

    def _generate_chunk_with_retry(
        self,
        text: str,
        chunk_size: int,
        min_chunk_size: int,
        max_retries: int
    ) -> Optional[np.ndarray]:
        """Generate audio for a chunk with automatic retry and splitting."""
        current_size = chunk_size
        attempts = 0

        while current_size >= min_chunk_size and attempts < max_retries * 3:
            try:
                # Check memory before generation
                mem_available = get_available_memory_gb()
                emergency_threshold = self.config['memory'].get('emergency_split_threshold', 2.0)

                if mem_available < emergency_threshold:
                    print(f"  [!] Low memory ({mem_available:.1f}GB) - reducing chunk size")
                    current_size = max(min_chunk_size, current_size // 2)
                    clear_mps_cache()

                chunks = split_into_chunks(text, current_size)
                audio_parts = []

                for i, chunk in enumerate(chunks):
                    try:
                        audio, _ = self._generate_audio(chunk)
                        audio_parts.append(audio)
                    except Exception as e:
                        if "out of memory" in str(e).lower() or "mps" in str(e).lower():
                            raise MemoryError(str(e))
                        raise

                if audio_parts:
                    return np.concatenate(audio_parts)
                return None

            except MemoryError:
                clear_mps_cache()
                current_size = max(min_chunk_size, current_size // 2)
                print(f"  [!] Memory error - retrying with chunk size {current_size}")
                attempts += 1

            except Exception as e:
                print(f"  [!] Error: {e}")
                attempts += 1
                time.sleep(self.config['conversion'].get('retry_delay', 5))

        return None

    def _generate_chapter_audio(
        self,
        chapter: Chapter,
        progress_callback: callable = None
    ) -> Optional[str]:
        """Generate audio for a single chapter and save to file."""
        conv_config = self.config['conversion']
        audio_parts = []

        # Generate chapter announcement
        if conv_config.get('announce_chapters', True):
            try:
                ann_audio, _ = self._generate_audio(chapter.title)
                audio_parts.append(ann_audio)
                audio_parts.append(self._create_silence(1.0))
            except Exception as e:
                print(f"  [!] Announcement failed: {e}")

        # Generate content in chunks
        chunk_size = conv_config.get('chunk_size', 1500)
        min_chunk_size = conv_config.get('min_chunk_size', 200)
        max_retries = conv_config.get('max_retries', 3)

        chunks = split_into_chunks(chapter.content, chunk_size)

        for i, chunk in enumerate(tqdm(chunks, desc=f"  {chapter.title[:25]}", leave=False)):
            if self._shutdown_requested:
                break

            audio = self._generate_chunk_with_retry(chunk, chunk_size, min_chunk_size, max_retries)
            if audio is not None:
                audio_parts.append(audio)

            if progress_callback:
                progress_callback(i + 1, len(chunks))

        if not audio_parts:
            return None

        # Add pause after chapter
        pause_duration = conv_config.get('chapter_pause', 2.5)
        audio_parts.append(self._create_silence(pause_duration))

        # Concatenate and save
        full_audio = np.concatenate(audio_parts)
        output_path = self.temp_dir / f"{chapter.id}.wav"
        sf.write(str(output_path), full_audio, self.sample_rate)

        return str(output_path)

    def _generate_simple_audio(self, text: str, output_id: str) -> Optional[str]:
        """Generate audio for simple text (intro/outro) and save to file."""
        try:
            print(f"  Generating: {text[:50]}...")
            audio, _ = self._generate_audio(text)
            # Add pause after
            audio_with_pause = np.concatenate([audio, self._create_silence(2.0)])
            output_path = self.temp_dir / f"{output_id}.wav"
            sf.write(str(output_path), audio_with_pause, self.sample_rate)
            return str(output_path)
        except Exception as e:
            print(f"  [!] Failed to generate {output_id}: {e}")
            return None

    def convert_epub(
        self,
        epub_path: str,
        output_path: str = None,
        state_path: str = None
    ) -> Optional[str]:
        """Convert EPUB to audiobook with chapters."""
        epub_path = Path(epub_path)
        book_name = epub_path.stem

        if output_path:
            output_path = Path(output_path)
        else:
            fmt = self.config['output'].get('format', 'm4b')
            output_path = self.output_dir / f"{book_name}.{fmt}"

        state_file = Path(state_path) if state_path else self.output_dir / f".{book_name}.progress.json"

        # Check for existing state (resume)
        state = None
        if state_file.exists():
            try:
                state = ConversionState.load(state_file)
                print(f"[*] Resuming from checkpoint ({len(state.chapters_completed)} chapters done)")
            except Exception:
                state = None

        if state is None:
            state = ConversionState(
                epub_path=str(epub_path),
                voice_path=self.voice_path,
                output_path=str(output_path),
                config_path=None,
                started_at=datetime.now().isoformat()
            )

        # Parse EPUB
        print(f"\n[*] Parsing EPUB: {epub_path.name}")
        parser = EPUBParser(str(epub_path)).parse()

        print(f"    Title: {parser.metadata.get('title', 'Unknown')}")
        print(f"    Author: {parser.metadata.get('author', 'Unknown')}")
        print(f"    Cover: {'Found' if parser.cover_path else 'Not found'}")

        # Get chapters with filtering
        include_ids = self.config['chapters'].get('include')
        exclude_ids = self.config['chapters'].get('exclude', [])
        text_cleaner = create_text_cleaner(self.config.get('text_cleaning', {}))

        chapters = parser.get_chapters(
            include_ids=include_ids,
            exclude_ids=exclude_ids,
            text_cleaner=text_cleaner
        )

        if not chapters:
            print("[!] No chapters to convert")
            return None

        state.chapters_total = len(chapters)
        state.save(state_file)

        # Show chapter list
        total_words = sum(ch.word_count for ch in chapters)
        print(f"\n[*] Chapters to convert: {len(chapters)} ({total_words:,} words)")
        for i, ch in enumerate(chapters[:10]):
            status = "[done]" if ch.id in state.chapters_completed else ""
            print(f"    {i+1:2}. {ch.title[:50]} ({ch.word_count:,} words) {status}")
        if len(chapters) > 10:
            print(f"    ... and {len(chapters) - 10} more")

        # Generate audio for each chapter
        print("\n" + "=" * 60)
        print("GENERATING AUDIO")
        print("=" * 60)

        chapter_audios = []
        current_time = 0.0

        # Generate intro if configured
        intro_text = self.config.get('intro_text')
        title_announcement = self.config.get('title_announcement')

        if intro_text and '_intro' not in state.chapters_completed:
            print("\n[INTRO]")
            audio_path = self._generate_simple_audio(intro_text, '_intro')
            if audio_path:
                audio_data, sr = sf.read(audio_path)
                duration = len(audio_data) / sr
                chapter_audios.append(ChapterAudio(
                    id='_intro',
                    title='Introduction',
                    audio_path=audio_path,
                    sample_rate=sr,
                    start_time=current_time,
                    duration=duration
                ))
                current_time += duration
                state.chapters_completed.append('_intro')
                state.chapter_audio_files['_intro'] = audio_path
                state.save(state_file)
                print(f"    [+] Duration: {duration:.1f} sec")

        if title_announcement and '_title' not in state.chapters_completed:
            print("\n[TITLE]")
            audio_path = self._generate_simple_audio(title_announcement, '_title')
            if audio_path:
                audio_data, sr = sf.read(audio_path)
                duration = len(audio_data) / sr
                chapter_audios.append(ChapterAudio(
                    id='_title',
                    title='Title',
                    audio_path=audio_path,
                    sample_rate=sr,
                    start_time=current_time,
                    duration=duration
                ))
                current_time += duration
                state.chapters_completed.append('_title')
                state.chapter_audio_files['_title'] = audio_path
                state.save(state_file)
                print(f"    [+] Duration: {duration:.1f} sec")

        for i, chapter in enumerate(chapters):
            if self._shutdown_requested:
                print("\n[!] Shutdown - saving progress")
                state.save(state_file)
                break

            # Skip already completed chapters
            if chapter.id in state.chapters_completed:
                # Load existing audio info
                audio_path = state.chapter_audio_files.get(chapter.id)
                if audio_path and Path(audio_path).exists():
                    audio_data, sr = sf.read(audio_path)
                    duration = len(audio_data) / sr
                    chapter_audios.append(ChapterAudio(
                        id=chapter.id,
                        title=chapter.title,
                        audio_path=audio_path,
                        sample_rate=sr,
                        start_time=current_time,
                        duration=duration
                    ))
                    current_time += duration
                    print(f"[{i+1}/{len(chapters)}] {chapter.title[:40]} [cached]")
                    continue

            print(f"\n[{i+1}/{len(chapters)}] {chapter.title}")
            print(f"    Words: {chapter.word_count:,}")
            print(f"    Memory: {get_available_memory_gb():.1f} GB")

            try:
                audio_path = self._generate_chapter_audio(chapter)

                if audio_path:
                    # Get duration
                    audio_data, sr = sf.read(audio_path)
                    duration = len(audio_data) / sr

                    chapter_audios.append(ChapterAudio(
                        id=chapter.id,
                        title=chapter.title,
                        audio_path=audio_path,
                        sample_rate=sr,
                        start_time=current_time,
                        duration=duration
                    ))
                    current_time += duration

                    # Update state
                    state.chapters_completed.append(chapter.id)
                    state.chapter_audio_files[chapter.id] = audio_path
                    state.save(state_file)

                    print(f"    [+] Duration: {duration/60:.1f} min")
                else:
                    print(f"    [!] Failed to generate audio")

            except Exception as e:
                print(f"    [!] Error: {e}")

            # Clear memory after each chapter
            if self.config['memory'].get('clear_cache_per_chapter', True):
                clear_mps_cache()

        # Generate outro if configured
        outro_text = self.config.get('outro_text')
        if outro_text and '_outro' not in state.chapters_completed and not self._shutdown_requested:
            print("\n[OUTRO]")
            audio_path = self._generate_simple_audio(outro_text, '_outro')
            if audio_path:
                audio_data, sr = sf.read(audio_path)
                duration = len(audio_data) / sr
                chapter_audios.append(ChapterAudio(
                    id='_outro',
                    title='Closing',
                    audio_path=audio_path,
                    sample_rate=sr,
                    start_time=current_time,
                    duration=duration
                ))
                current_time += duration
                state.chapters_completed.append('_outro')
                state.chapter_audio_files['_outro'] = audio_path
                state.save(state_file)
                print(f"    [+] Duration: {duration:.1f} sec")

        if not chapter_audios:
            print("[!] No audio generated")
            return None

        # Save final audiobook
        print("\n" + "=" * 60)
        print("CREATING AUDIOBOOK")
        print("=" * 60)

        final_path = self._save_audiobook(
            chapter_audios,
            str(output_path),
            parser.metadata,
            parser.cover_path
        )

        if final_path:
            total_duration = sum(ca.duration for ca in chapter_audios)
            print(f"\n[+] Total duration: {total_duration/60:.1f} minutes")
            print(f"[+] Output: {final_path}")

            # Mark complete
            state.completed = True
            state.save(state_file)

            # Cleanup temp files
            self._cleanup_temp()

        return final_path

    def _save_audiobook(
        self,
        chapter_audios: List[ChapterAudio],
        output_path: str,
        metadata: dict,
        cover_path: str = None
    ) -> Optional[str]:
        """Save audiobook with chapter markers."""
        output_format = self.config['output'].get('format', 'm4b')

        # Concatenate all audio
        print("[*] Combining chapter audio...")
        all_audio_parts = []
        for ca in tqdm(chapter_audios, desc="Loading chapters"):
            audio_data, _ = sf.read(ca.audio_path)
            all_audio_parts.append(audio_data)

        all_audio = np.concatenate(all_audio_parts)
        sample_rate = chapter_audios[0].sample_rate

        # Save as WAV first
        wav_path = str(self.temp_dir / "combined.wav")
        sf.write(wav_path, all_audio, sample_rate)

        if output_format == 'wav':
            import shutil
            shutil.move(wav_path, output_path)
            return output_path

        # Create M4B with chapters
        try:
            metadata_path = self._create_ffmetadata(chapter_audios, metadata)
            bitrate = self.config['output'].get('bitrate', '128k')

            cmd = [
                "ffmpeg", "-y",
                "-i", wav_path,
                "-i", metadata_path,
                "-map", "0:a",
                "-map_metadata", "1",
                "-c:a", "aac",
                "-b:a", bitrate,
            ]

            # Add cover if available
            if cover_path and self.config['output'].get('embed_cover', True):
                if Path(cover_path).exists():
                    cmd.extend([
                        "-i", cover_path,
                        "-map", "2:v",
                        "-c:v", "mjpeg",
                        "-disposition:v:0", "attached_pic"
                    ])

            cmd.append(output_path)

            print(f"[*] Creating {output_format.upper()} with chapters...")
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode != 0:
                print(f"[!] FFmpeg error - saving as WAV")
                import shutil
                wav_output = output_path.replace(f'.{output_format}', '.wav')
                shutil.move(wav_path, wav_output)
                return wav_output

            # Cleanup
            Path(wav_path).unlink(missing_ok=True)
            Path(metadata_path).unlink(missing_ok=True)

            return output_path

        except FileNotFoundError:
            print("[!] FFmpeg not found - saving as WAV")
            import shutil
            wav_output = output_path.replace(f'.{output_format}', '.wav')
            shutil.move(wav_path, wav_output)
            return wav_output

    def _create_ffmetadata(self, chapter_audios: List[ChapterAudio], metadata: dict) -> str:
        """Create FFMETADATA file for chapter markers."""
        lines = [";FFMETADATA1"]
        lines.append(f"title={metadata.get('title', 'Audiobook')}")
        lines.append(f"artist={metadata.get('author', 'Unknown')}")
        lines.append(f"album={metadata.get('title', 'Audiobook')}")
        lines.append("")

        for ca in chapter_audios:
            start_ms = int(ca.start_time * 1000)
            end_ms = int((ca.start_time + ca.duration) * 1000)

            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={start_ms}")
            lines.append(f"END={end_ms}")
            lines.append(f"title={ca.title}")
            lines.append("")

        metadata_path = str(self.temp_dir / "ffmetadata.txt")
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return metadata_path

    def _cleanup_temp(self):
        """Clean up temporary files."""
        try:
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        except Exception:
            pass

    def dry_run(self, epub_path: str):
        """Show what would be converted without generating audio."""
        print(f"\n[DRY RUN] Parsing EPUB: {epub_path}")

        parser = EPUBParser(epub_path).parse()

        print(f"\n{'=' * 60}")
        print("BOOK METADATA")
        print(f"{'=' * 60}")
        print(f"Title:  {parser.metadata.get('title', 'Unknown')}")
        print(f"Author: {parser.metadata.get('author', 'Unknown')}")
        print(f"Cover:  {'Found' if parser.cover_path else 'Not found'}")

        # Show intro/outro config
        intro_text = self.config.get('intro_text')
        title_announcement = self.config.get('title_announcement')
        outro_text = self.config.get('outro_text')

        if intro_text or title_announcement or outro_text:
            print(f"\n{'=' * 60}")
            print("INTRO/OUTRO")
            print(f"{'=' * 60}")
            if intro_text:
                print(f"Intro:  \"{intro_text}\"")
            if title_announcement:
                print(f"Title:  \"{title_announcement}\"")
            if outro_text:
                print(f"Outro:  \"{outro_text}\"")

        print(f"\n{'=' * 60}")
        print("ALL CHAPTERS IN SPINE (use these IDs in config)")
        print(f"{'=' * 60}")

        all_chapters = parser.get_all_chapter_ids()
        for i, (item_id, title) in enumerate(all_chapters):
            print(f"{i+1:2}. {item_id:25} -> {title[:40]}")

        print(f"\n{'=' * 60}")
        print("CHAPTERS AFTER FILTERING")
        print(f"{'=' * 60}")

        include_ids = self.config['chapters'].get('include')
        exclude_ids = self.config['chapters'].get('exclude', [])
        text_cleaner = create_text_cleaner(self.config.get('text_cleaning', {}))

        chapters = parser.get_chapters(
            include_ids=include_ids,
            exclude_ids=exclude_ids,
            text_cleaner=text_cleaner
        )

        total_words = 0
        for i, ch in enumerate(chapters):
            print(f"{i+1:2}. {ch.id:25} {ch.word_count:6,} words  {ch.title[:35]}")
            total_words += ch.word_count

        print(f"\n{'=' * 60}")
        print(f"SUMMARY: {len(chapters)} chapters, {total_words:,} words")
        print(f"{'=' * 60}")


# ============================================================
# CLI
# ============================================================

def load_config(config_path: Optional[str]) -> dict:
    """Load configuration from YAML file."""
    if not config_path:
        return {}

    config_path = Path(config_path)
    if not config_path.exists():
        print(f"[!] Config file not found: {config_path}")
        return {}

    with open(config_path, 'r') as f:
        return yaml.safe_load(f) or {}


def find_transcript(voice_path: str) -> Optional[str]:
    """Auto-detect transcript file next to voice sample."""
    voice_path = Path(voice_path)
    potential_names = [
        voice_path.with_suffix('.txt'),
        voice_path.parent / f"{voice_path.stem}_transcript.txt",
        voice_path.parent / f"{voice_path.stem}.transcript.txt",
    ]

    for path in potential_names:
        if path.exists():
            return str(path)

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Convert EPUB/PDF to voice-cloned audiobook",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic conversion
  python convert_audiobook.py --epub book.epub --voice sample.wav

  # With custom config
  python convert_audiobook.py --epub book.epub --voice sample.wav --config chapters.yaml

  # Dry run (show chapters without converting)
  python convert_audiobook.py --epub book.epub --dry-run

  # Resume interrupted conversion
  python convert_audiobook.py --epub book.epub --voice sample.wav --resume
        """
    )

    parser.add_argument('--epub', '-e', type=str, help='Path to EPUB file (required for conversion)')
    parser.add_argument('--voice', '-v', type=str, help='Path to voice sample WAV file')
    parser.add_argument('--transcript', '-t', type=str, help='Path to transcript of voice sample (auto-detected if not provided)')
    parser.add_argument('--config', '-c', type=str, help='Path to YAML config file')
    parser.add_argument('--output', '-o', type=str, help='Output file path')
    parser.add_argument('--output-dir', type=str, default='audiobooks', help='Output directory (default: audiobooks)')
    parser.add_argument('--dry-run', action='store_true', help='Show chapters without converting')
    parser.add_argument('--resume', action='store_true', help='Resume interrupted conversion')

    args = parser.parse_args()

    # Validate args
    if not args.epub:
        # Interactive prompt
        print("EPUB file path:")
        args.epub = input().strip().strip("'\"")

    if not args.epub or not Path(args.epub).exists():
        print(f"[!] EPUB file not found: {args.epub}")
        sys.exit(1)

    # Load config
    config = load_config(args.config)

    # Dry run mode
    if args.dry_run:
        converter = AudiobookConverter(
            voice_path="",
            config=config,
            output_dir=Path(args.output_dir)
        )
        converter.dry_run(args.epub)
        return

    # Voice sample required for actual conversion
    if not args.voice:
        print("Voice sample path:")
        args.voice = input().strip().strip("'\"")

    if not args.voice or not Path(args.voice).exists():
        print(f"[!] Voice sample not found: {args.voice}")
        sys.exit(1)

    # Auto-detect transcript
    transcript_path = args.transcript
    if not transcript_path:
        transcript_path = find_transcript(args.voice)
        if transcript_path:
            print(f"[*] Auto-detected transcript: {transcript_path}")

    # Create converter
    converter = AudiobookConverter(
        voice_path=args.voice,
        transcript_path=transcript_path,
        config=config,
        output_dir=Path(args.output_dir)
    )

    # Load models
    converter.load_models()

    # Convert
    result = converter.convert_epub(
        epub_path=args.epub,
        output_path=args.output
    )

    if result:
        print(f"\n[+] Conversion complete: {result}")
    else:
        print("\n[!] Conversion failed or incomplete")
        sys.exit(1)


if __name__ == "__main__":
    main()
