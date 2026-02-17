"""
TTS engines: MLX (local, Apple Silicon) and OpenAI API (cloud).
"""

import base64
import io
import json
import logging
import os
import re
import shutil
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field, asdict
from datetime import datetime
from html import unescape
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import soundfile as sf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# MLX (local)
MLX_SPEAKERS = ["Vivian", "Serena", "Uncle_Fu", "Dylan", "Eric", "Ryan", "Aiden"]
MLX_LANGUAGES = ["auto", "chinese", "english", "japanese", "korean"]
SAMPLE_RATE = 24000
MLX_MODEL_IDS = {
    "custom_voice": "mlx-community/Qwen3-TTS-12Hz-1.7B-CustomVoice-8bit",
    "voice_clone":  "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-bf16",
    "voice_design": "mlx-community/Qwen3-TTS-12Hz-1.7B-VoiceDesign-bf16",
}

# OpenAI API
OPENAI_VOICES = [
    "alloy", "ash", "ballad", "cedar", "coral", "echo",
    "fable", "marin", "nova", "onyx", "sage", "shimmer", "verse",
]
OPENAI_MODELS = ["gpt-4o-mini-tts", "tts-1", "tts-1-hd"]

# ---------------------------------------------------------------------------
# Text extraction (standalone, no PyTorch)
# ---------------------------------------------------------------------------

try:
    from bs4 import BeautifulSoup
    _BS4 = True
except ImportError:
    _BS4 = False

try:
    import PyPDF2
    _PDF = True
except ImportError:
    _PDF = False

try:
    import ebooklib
    from ebooklib import epub
    _EPUB = True
except ImportError:
    _EPUB = False


def _clean_html(html: str) -> str:
    if not html:
        return ""
    if _BS4:
        try:
            soup = BeautifulSoup(html, "html.parser")
            for t in soup(["script", "style"]):
                t.decompose()
            return " ".join(soup.get_text().split())
        except Exception:
            pass
    html = re.sub(r"<(style|script)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    return " ".join(unescape(html).split())


def _clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\b\d{1,3}\b(?=\s|$)", "", text)
    return text.strip()


def extract_text_from_file(file_path: Path) -> str:
    ext = file_path.suffix.lower()

    if ext == ".txt":
        for enc in ["utf-8", "utf-16", "latin-1", "cp1252"]:
            try:
                return _clean_text(file_path.read_text(encoding=enc))
            except UnicodeDecodeError:
                continue
        raise ValueError("Could not decode text file")

    if ext == ".pdf":
        if not _PDF:
            raise ImportError("PyPDF2 required for PDF")
        parts = []
        with open(file_path, "rb") as f:
            for page in PyPDF2.PdfReader(f).pages:
                t = page.extract_text()
                if t and t.strip():
                    parts.append(t)
        return _clean_text("\n\n".join(parts))

    if ext == ".epub":
        if not _EPUB:
            raise ImportError("ebooklib required for EPUB")
        try:
            book = epub.read_epub(str(file_path))
            parts = []
            for item_id, _ in book.spine:
                item = book.get_item_by_id(item_id)
                if item and isinstance(item, ebooklib.ITEM_DOCUMENT):
                    content = item.get_body_content()
                    if content:
                        if isinstance(content, bytes):
                            content = content.decode("utf-8", errors="ignore")
                        clean = _clean_html(str(content))
                        if clean.strip():
                            parts.append(clean)
            if parts:
                return "\n\n".join(parts)
        except Exception:
            pass
        # Zipfile fallback
        parts = []
        with zipfile.ZipFile(file_path, "r") as zf:
            for name in zf.namelist():
                if name.lower().endswith((".html", ".xhtml", ".htm")):
                    try:
                        clean = _clean_html(zf.read(name).decode("utf-8", errors="ignore"))
                        if clean.strip():
                            parts.append(clean)
                    except Exception:
                        continue
        return "\n\n".join(parts)

    raise ValueError(f"Unsupported format: {ext}")


def _break_long_text(text: str, max_chars: int) -> List[str]:
    """Split text that exceeds max_chars at word boundaries."""
    words = text.split()
    pieces, current = [], ""
    for w in words:
        candidate = f"{current} {w}".strip() if current else w
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                pieces.append(current)
            current = w
    if current:
        pieces.append(current)
    return pieces


def split_into_chunks(
    text: str, chunk_size: int = 1500, max_chars: Optional[int] = None,
) -> List[str]:
    if not text.strip():
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current, words = [], "", 0
    for s in sentences:
        # If a single sentence exceeds max_chars, break it at word boundaries
        if max_chars and len(s) > max_chars:
            if current:
                chunks.append(current.strip())
                current, words = "", 0
            chunks.extend(_break_long_text(s, max_chars))
            continue

        sw = len(s.split())
        would_exceed_words = words + sw > chunk_size
        would_exceed_chars = max_chars and len(current) + len(s) + 1 > max_chars
        if would_exceed_words or would_exceed_chars:
            if current:
                chunks.append(current.strip())
            current = s + " "
            words = sw
        else:
            current += s + " "
            words += sw
    if current.strip():
        chunks.append(current.strip())
    return [c for c in chunks if c.strip()]


# ---------------------------------------------------------------------------
# Text cleaning utilities
# ---------------------------------------------------------------------------

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
    """Remove footnote symbols like *, †, ‡, §, etc."""
    markers = r'[*\u2020\u2021\u00a7\u00b6\u2016\u00b9\u00b2\u00b3\u2074\u2075\u2076\u2077\u2078\u2079\u2070]+'
    text = re.sub(r'\s*' + markers + r'\s*', ' ', text)
    return re.sub(r'\s+', ' ', text)


def normalize_special_chars(text: str) -> str:
    """Normalize special characters for better TTS output."""
    text = text.replace('\u2014', ' - ')
    text = text.replace('\u2013', ' - ')
    text = text.replace('\u201c', '"').replace('\u201d', '"')
    text = text.replace('\u2018', "'").replace('\u2019', "'")
    text = text.replace('\u2026', '...')
    return text


def apply_text_cleaning(text: str, fix_capitals: bool = True, remove_footnotes: bool = True, normalize_chars: bool = True) -> str:
    """Apply all text cleaning steps based on toggles."""
    if fix_capitals:
        text = fix_spaced_capitals(text)
    if remove_footnotes:
        text = remove_footnote_markers(text)
    if normalize_chars:
        text = normalize_special_chars(text)
    return re.sub(r'\s+', ' ', text).strip()


# ---------------------------------------------------------------------------
# Device and memory info
# ---------------------------------------------------------------------------

def get_device_info() -> dict:
    """Get device and memory information for status display."""
    info = {"device": "CPU", "memory_available_gb": 0.0, "memory_total_gb": 0.0, "accelerator": None}
    try:
        import psutil
        mem = psutil.virtual_memory()
        info["memory_available_gb"] = round(mem.available / (1024 ** 3), 1)
        info["memory_total_gb"] = round(mem.total / (1024 ** 3), 1)
    except ImportError:
        pass
    try:
        import mlx.core as mx
        info["device"] = "Apple Silicon (MLX)"
        info["accelerator"] = "Metal"
    except ImportError:
        pass
    return info


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------

# OpenAI TTS pricing (per 1M characters)
OPENAI_TTS_PRICING = {
    "tts-1": 15.00,
    "tts-1-hd": 30.00,
    "gpt-4o-mini-tts": 12.00,
}


def estimate_openai_cost(text: str, model: str = "gpt-4o-mini-tts") -> dict:
    """Estimate the OpenAI API cost for generating speech from text."""
    char_count = len(text)
    price_per_million = OPENAI_TTS_PRICING.get(model, 12.00)
    cost = (char_count / 1_000_000) * price_per_million
    return {
        "characters": char_count,
        "model": model,
        "price_per_million_chars": price_per_million,
        "estimated_cost_usd": round(cost, 4),
        "estimated_duration_min": round(char_count / 1000, 1),  # rough ~1000 chars/min
    }


# ---------------------------------------------------------------------------
# EPUB metadata and chapter extraction
# ---------------------------------------------------------------------------

class BookMetadata:
    """Lightweight book metadata container."""
    def __init__(self):
        self.title: str = "Unknown"
        self.author: str = "Unknown"
        self.chapters: List[dict] = []  # [{"id": str, "title": str, "word_count": int}]
        self.total_words: int = 0
        self.cover_image: Optional[str] = None  # base64 data URI or None
        self.format: str = ""

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "author": self.author,
            "chapters": self.chapters,
            "total_words": self.total_words,
            "has_cover": self.cover_image is not None,
            "format": self.format,
        }


def extract_book_metadata(file_path: Path) -> BookMetadata:
    """Extract metadata and chapter list from a book file."""
    meta = BookMetadata()
    ext = file_path.suffix.lower()
    meta.format = ext.lstrip(".")

    if ext == ".epub" and _EPUB:
        try:
            _NS = {
                'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
                'opf': 'http://www.idpf.org/2007/opf',
                'dc': 'http://purl.org/dc/elements/1.1/',
                'ncx': 'http://www.daisy.org/z3986/2005/ncx/',
            }
            with zipfile.ZipFile(str(file_path), 'r') as z:
                # Find OPF
                container = z.read('META-INF/container.xml').decode('utf-8')
                root = ET.fromstring(container)
                rootfile = root.find('.//container:rootfile', _NS)
                opf_path = rootfile.get('full-path')
                opf_dir = str(Path(opf_path).parent)
                if opf_dir == '.':
                    opf_dir = ''

                # Parse OPF for metadata + manifest + spine
                opf_content = z.read(opf_path).decode('utf-8')
                opf_root = ET.fromstring(opf_content)

                md = opf_root.find('opf:metadata', _NS)
                if md is not None:
                    t = md.find('dc:title', _NS)
                    a = md.find('dc:creator', _NS)
                    meta.title = t.text if t is not None and t.text else "Unknown"
                    meta.author = a.text if a is not None and a.text else "Unknown"

                    # Find cover ID
                    cover_id = None
                    for m in md.findall('opf:meta', _NS):
                        if m.get('name') == 'cover':
                            cover_id = m.get('content')

                # Build manifest
                manifest = {}
                mf = opf_root.find('opf:manifest', _NS)
                if mf is not None:
                    for item in mf.findall('opf:item', _NS):
                        manifest[item.get('id')] = {
                            'href': item.get('href'),
                            'media_type': item.get('media-type'),
                        }

                # Extract cover image as base64
                if cover_id and cover_id in manifest:
                    cover_href = manifest[cover_id]['href']
                    cover_path = f"{opf_dir}/{cover_href}" if opf_dir else cover_href
                    try:
                        cover_data = z.read(cover_path)
                        mime = manifest[cover_id].get('media_type', 'image/jpeg')
                        b64 = base64.b64encode(cover_data).decode('ascii')
                        meta.cover_image = f"data:{mime};base64,{b64}"
                    except Exception:
                        pass

                # Build spine
                spine = []
                sp = opf_root.find('opf:spine', _NS)
                if sp is not None:
                    for itemref in sp.findall('opf:itemref', _NS):
                        idref = itemref.get('idref')
                        linear = itemref.get('linear', 'yes')
                        if linear == 'yes' and idref in manifest:
                            mt = manifest[idref]['media_type']
                            if mt in ('application/xhtml+xml', 'text/html'):
                                spine.append(idref)

                # Parse NCX for chapter titles
                ncx_titles = {}
                for item_id, item in manifest.items():
                    if item['media_type'] == 'application/x-dtbncx+xml':
                        ncx_href = item['href']
                        ncx_path = f"{opf_dir}/{ncx_href}" if opf_dir else ncx_href
                        try:
                            ncx_content = z.read(ncx_path).decode('utf-8')
                            ncx_root = ET.fromstring(ncx_content)
                            for navpoint in ncx_root.findall('.//ncx:navPoint', _NS):
                                label = navpoint.find('ncx:navLabel/ncx:text', _NS)
                                content = navpoint.find('ncx:content', _NS)
                                if label is not None and content is not None:
                                    src = content.get('src')
                                    file_ref = src.split('#')[0] if src else None
                                    if file_ref and label.text:
                                        ncx_titles[file_ref] = label.text
                        except Exception:
                            pass
                        break

                # Build chapter list with word counts
                total_words = 0
                for item_id in spine:
                    item = manifest[item_id]
                    href = item['href']
                    file_p = f"{opf_dir}/{href}" if opf_dir else href
                    title = ncx_titles.get(href, item_id)
                    try:
                        content = z.read(file_p).decode('utf-8', errors='ignore')
                        clean = _clean_html(content)
                        wc = len(clean.split()) if clean.strip() else 0
                    except Exception:
                        wc = 0
                    if wc > 0:
                        meta.chapters.append({"id": item_id, "title": title, "word_count": wc})
                        total_words += wc
                meta.total_words = total_words
        except Exception as e:
            logger.warning(f"Failed to parse EPUB metadata: {e}")

    elif ext == ".pdf" and _PDF:
        try:
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                info = reader.metadata
                if info:
                    meta.title = info.get('/Title', 'Unknown') or 'Unknown'
                    meta.author = info.get('/Author', 'Unknown') or 'Unknown'
                total_words = 0
                for i, page in enumerate(reader.pages):
                    t = page.extract_text()
                    wc = len(t.split()) if t else 0
                    if wc > 0:
                        meta.chapters.append({"id": f"page_{i+1}", "title": f"Page {i+1}", "word_count": wc})
                        total_words += wc
                meta.total_words = total_words
        except Exception as e:
            logger.warning(f"Failed to parse PDF metadata: {e}")

    elif ext == ".txt":
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
            meta.title = file_path.stem.replace("_", " ").title()
            wc = len(text.split())
            meta.total_words = wc
            meta.chapters.append({"id": "full_text", "title": "Full Text", "word_count": wc})
        except Exception:
            pass

    return meta


# ---------------------------------------------------------------------------
# Conversion state for resume capability
# ---------------------------------------------------------------------------

@dataclass
class ConversionProgress:
    """Tracks audiobook conversion progress for resume capability."""
    file_path: str
    output_path: str
    total_chunks: int = 0
    completed_chunks: int = 0
    failed_chunks: List[int] = field(default_factory=list)
    started_at: str = ""
    updated_at: str = ""
    completed: bool = False

    def save(self, path: Path):
        self.updated_at = datetime.now().isoformat()
        with open(path, 'w') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'ConversionProgress':
        with open(path, 'r') as f:
            data = json.load(f)
        return cls(**data)

    @property
    def progress_fraction(self) -> float:
        if self.total_chunks == 0:
            return 0.0
        return self.completed_chunks / self.total_chunks


# ---------------------------------------------------------------------------
# Output format constants
# ---------------------------------------------------------------------------

OUTPUT_FORMATS = {
    "wav": {"label": "WAV (Lossless)", "ext": ".wav", "description": "Uncompressed, highest quality"},
    "mp3": {"label": "MP3", "ext": ".mp3", "description": "Compressed, widely compatible"},
    "m4b": {"label": "M4B (Audiobook)", "ext": ".m4b", "description": "Audiobook format with chapters"},
}


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class MLXTTSEngine:
    def __init__(self):
        self.model = None
        self._current_id: Optional[str] = None

    def load_model(self, voice_mode: str) -> str:
        model_id = MLX_MODEL_IDS[voice_mode]
        if self._current_id == model_id and self.model is not None:
            return model_id
        self.unload_model()
        logger.info(f"Loading {model_id}...")
        from mlx_audio.tts.utils import load_model
        self.model = load_model(model_id)
        self._current_id = model_id
        return model_id

    def unload_model(self):
        if self.model is not None:
            import mlx.core as mx
            del self.model
            self.model = None
            self._current_id = None
            mx.metal.clear_cache()

    @property
    def is_loaded(self) -> bool:
        return self.model is not None

    @property
    def current_model_id(self) -> Optional[str]:
        return self._current_id

    def generate_speech(
        self,
        text: str,
        voice_mode: str = "custom_voice",
        speaker: str = "Ryan",
        language: str = "english",
        instruct: Optional[str] = None,
        ref_audio: Optional[str] = None,
        ref_text: Optional[str] = None,
        voice_description: Optional[str] = None,
        progress_callback=None,
    ) -> Tuple[np.ndarray, int]:
        if progress_callback:
            progress_callback(0.05, "Loading model...")
        self.load_model(voice_mode)
        if progress_callback:
            progress_callback(0.15, "Model ready, generating...")

        if voice_mode == "custom_voice":
            gen = self.model.generate_custom_voice(
                text=text, speaker=speaker, language=language,
                instruct=instruct or "",
            )
        elif voice_mode == "voice_clone":
            if not ref_audio:
                raise ValueError("Voice clone requires reference audio")
            gen = self.model.generate(
                text=text, ref_audio=ref_audio,
                ref_text=ref_text or "", lang_code=language,
            )
        elif voice_mode == "voice_design":
            if not voice_description:
                raise ValueError("Voice design requires a description")
            gen = self.model.generate_voice_design(
                text=text, instruct=voice_description, language=language,
            )
        else:
            raise ValueError(f"Unknown voice mode: {voice_mode}")

        # Iterate generator manually to report progress per segment
        results = []
        for i, result in enumerate(gen):
            results.append(result)
            if progress_callback:
                # We don't know total segments ahead of time, so use a formula
                # that approaches 0.90 but never quite reaches it
                frac = 0.15 + 0.75 * (1 - 1 / (i + 2))
                progress_callback(frac, f"Generated segment {i + 1}...")

        if not results:
            raise RuntimeError("No audio generated")

        if progress_callback:
            progress_callback(0.93, "Concatenating audio...")

        import mlx.core as mx
        audio = mx.concatenate([r.audio for r in results], axis=0)
        if progress_callback:
            progress_callback(0.97, "Finalizing...")
        return np.array(audio), SAMPLE_RATE

    def generate_audiobook(
        self, file_path: str, voice_mode: str = "custom_voice",
        output_path: str = "audiobooks/output.wav",
        speaker: str = "Ryan", language: str = "english",
        instruct: Optional[str] = None,
        ref_audio: Optional[str] = None, ref_text: Optional[str] = None,
        voice_description: Optional[str] = None,
        progress_callback=None,
    ) -> str:
        fp = Path(file_path)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        text = extract_text_from_file(fp)
        if not text.strip():
            raise ValueError("No text extracted")
        chunks = split_into_chunks(text)
        total = len(chunks)
        if total == 0:
            raise ValueError("No chunks created")

        # Resume / checkpoint setup
        chunks_dir = out.parent / f".{out.stem}_chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        progress_file = out.parent / f".{out.stem}.progress.json"

        if progress_file.exists():
            try:
                progress = ConversionProgress.load(progress_file)
                if progress.completed or progress.total_chunks != total:
                    progress = ConversionProgress(
                        file_path=str(fp), output_path=str(out),
                        total_chunks=total, started_at=datetime.now().isoformat(),
                    )
            except Exception:
                progress = ConversionProgress(
                    file_path=str(fp), output_path=str(out),
                    total_chunks=total, started_at=datetime.now().isoformat(),
                )
        else:
            progress = ConversionProgress(
                file_path=str(fp), output_path=str(out),
                total_chunks=total, started_at=datetime.now().isoformat(),
            )
        progress.save(progress_file)

        self.load_model(voice_mode)

        for i, chunk in enumerate(chunks):
            chunk_file = chunks_dir / f"chunk_{i:05d}.npy"
            if chunk_file.exists():
                if progress_callback:
                    progress_callback((i + 1) / total, f"Chunk {i + 1}/{total} (cached)")
                continue
            if progress_callback:
                progress_callback(i / total, f"Chunk {i + 1}/{total}")
            try:
                audio, _ = self.generate_speech(
                    text=chunk, voice_mode=voice_mode, speaker=speaker,
                    language=language, instruct=instruct, ref_audio=ref_audio,
                    ref_text=ref_text, voice_description=voice_description,
                )
                np.save(str(chunk_file), audio)
                progress.completed_chunks = i + 1
                progress.save(progress_file)
            except Exception as e:
                logger.error(f"Chunk {i + 1}/{total} failed: {e}")
                continue

        # Concatenate all saved chunks
        parts: List[np.ndarray] = []
        for i in range(total):
            chunk_file = chunks_dir / f"chunk_{i:05d}.npy"
            if chunk_file.exists():
                parts.append(np.load(str(chunk_file)))

        if not parts:
            raise RuntimeError("All chunks failed")

        sf.write(str(out), np.concatenate(parts), SAMPLE_RATE)
        progress.completed = True
        progress.save(progress_file)
        shutil.rmtree(str(chunks_dir))
        if progress_callback:
            progress_callback(1.0, "Done!")
        return str(out)


# ---------------------------------------------------------------------------
# OpenAI API Engine
# ---------------------------------------------------------------------------

def _get_openai_api_key() -> Optional[str]:
    """Get API key from environment (loaded from ~/.zshrc via shell)."""
    return os.environ.get("OPENAI_API_KEY")


class OpenAITTSEngine:
    def __init__(self):
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            from openai import OpenAI
            key = _get_openai_api_key()
            if not key:
                raise ValueError(
                    "OPENAI_API_KEY not found. Set it in ~/.zshrc or environment."
                )
            self._client = OpenAI(api_key=key)

    @staticmethod
    def api_key_available() -> bool:
        return bool(_get_openai_api_key())

    def _call_api(
        self, text: str, voice: str, model: str, instructions: Optional[str],
    ) -> Tuple[np.ndarray, int]:
        """Single API call for text that fits within the token limit."""
        kwargs = dict(model=model, voice=voice, input=text, response_format="wav")
        if instructions and model == "gpt-4o-mini-tts":
            kwargs["instructions"] = instructions
        response = self._client.audio.speech.create(**kwargs)
        audio_data, sr = sf.read(io.BytesIO(response.content))
        return audio_data.astype(np.float32), sr

    def generate_speech(
        self,
        text: str,
        voice: str = "coral",
        model: str = "gpt-4o-mini-tts",
        instructions: Optional[str] = None,
        progress_callback=None,
    ) -> Tuple[np.ndarray, int]:
        """Generate speech via OpenAI API. Auto-chunks long text seamlessly."""
        self._ensure_client()

        # Short text: single API call
        if len(text) <= 4000:
            if progress_callback:
                progress_callback(0.15, "Sending to OpenAI API...")
            audio, sr = self._call_api(text, voice, model, instructions)
            if progress_callback:
                progress_callback(0.95, "Audio received")
            return audio, sr

        # Long text: chunk, generate each, stitch together
        chunks = split_into_chunks(text, chunk_size=300, max_chars=4000)
        total = len(chunks)
        if progress_callback:
            progress_callback(0.10, f"Split into {total} chunks...")
        parts: List[np.ndarray] = []
        target_sr = None
        for i, chunk in enumerate(chunks):
            if progress_callback:
                progress_callback(0.10 + 0.80 * (i / total), f"Chunk {i + 1}/{total}...")
            audio, sr = self._call_api(chunk, voice, model, instructions)
            parts.append(audio)
            if target_sr is None:
                target_sr = sr

        if progress_callback:
            progress_callback(0.95, "Stitching audio...")
        return np.concatenate(parts), target_sr or 24000

    def generate_audiobook(
        self,
        file_path: str,
        output_path: str = "audiobooks/output.wav",
        voice: str = "coral",
        model: str = "gpt-4o-mini-tts",
        instructions: Optional[str] = None,
        progress_callback=None,
    ) -> str:
        fp = Path(file_path)
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        text = extract_text_from_file(fp)
        if not text.strip():
            raise ValueError("No text extracted")

        # OpenAI TTS API has a 2000-token input limit (~4 chars/token)
        chunks = split_into_chunks(text, chunk_size=300, max_chars=4000)
        total = len(chunks)
        if total == 0:
            raise ValueError("No chunks created")

        # Resume / checkpoint setup
        chunks_dir = out.parent / f".{out.stem}_chunks"
        chunks_dir.mkdir(parents=True, exist_ok=True)
        progress_file = out.parent / f".{out.stem}.progress.json"

        if progress_file.exists():
            try:
                progress = ConversionProgress.load(progress_file)
                if progress.completed or progress.total_chunks != total:
                    progress = ConversionProgress(
                        file_path=str(fp), output_path=str(out),
                        total_chunks=total, started_at=datetime.now().isoformat(),
                    )
            except Exception:
                progress = ConversionProgress(
                    file_path=str(fp), output_path=str(out),
                    total_chunks=total, started_at=datetime.now().isoformat(),
                )
        else:
            progress = ConversionProgress(
                file_path=str(fp), output_path=str(out),
                total_chunks=total, started_at=datetime.now().isoformat(),
            )
        progress.save(progress_file)

        target_sr = None

        for i, chunk in enumerate(chunks):
            chunk_file = chunks_dir / f"chunk_{i:05d}.npy"
            if chunk_file.exists():
                if target_sr is None:
                    # Recover sample rate from the first available chunk
                    _cached = np.load(str(chunk_file))
                    # We can't recover sr from npy; will get it from next generate call or default
                if progress_callback:
                    progress_callback((i + 1) / total, f"Chunk {i + 1}/{total} (cached)")
                continue
            if progress_callback:
                progress_callback(i / total, f"Chunk {i + 1}/{total}")
            try:
                audio, sr = self.generate_speech(
                    text=chunk, voice=voice, model=model,
                    instructions=instructions,
                )
                np.save(str(chunk_file), audio)
                if target_sr is None:
                    target_sr = sr
                progress.completed_chunks = i + 1
                progress.save(progress_file)
            except Exception as e:
                logger.error(f"Chunk {i + 1}/{total} failed: {e}")
                continue

        # Concatenate all saved chunks
        parts: List[np.ndarray] = []
        for i in range(total):
            chunk_file = chunks_dir / f"chunk_{i:05d}.npy"
            if chunk_file.exists():
                parts.append(np.load(str(chunk_file)))

        if not parts:
            raise RuntimeError("All chunks failed")

        sf.write(str(out), np.concatenate(parts), target_sr or 24000)
        progress.completed = True
        progress.save(progress_file)
        shutil.rmtree(str(chunks_dir))
        if progress_callback:
            progress_callback(1.0, "Done!")
        return str(out)
