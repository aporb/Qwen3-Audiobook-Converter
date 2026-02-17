#!/usr/bin/env python3
"""
OpenAI Audiobook Converter - Main Entry Point

Converts EPUB and PDF books to audiobooks using OpenAI's GPT-4o-mini TTS API.
Supports chapter markers, cover art embedding, and resume capability.
PDF support includes OCR fallback using OpenAI Vision API for scanned pages.

Usage:
    python convert.py --input book.epub --config chapters.yaml
    python convert.py --input book.pdf --voice coral --dry-run
    python convert.py --epub book.epub --voice coral  # Legacy support
"""

import argparse
import os
import sys
import signal
from pathlib import Path
from typing import Optional, Dict, List
from datetime import datetime

import yaml
from tqdm import tqdm

from epub_parser import EPUBParser, ParsedBook, Chapter
from pdf_parser import PDFParser
from chunker import TokenAwareChunker, count_tokens
from tts_client import TTSClient, AVAILABLE_VOICES
from audio_assembler import AudioAssembler, AudioSegment
from cost_estimator import CostEstimator, CostEstimate
from progress import ProgressManager, ConversionState

# Supported file formats
SUPPORTED_FORMATS = ['.epub', '.pdf']


# Default settings
DEFAULT_VOICE = "coral"
DEFAULT_BITRATE = "128k"
DEFAULT_CHUNK_PAUSE = 2.5  # seconds between chapters


class AudiobookConverter:
    """Main converter orchestrating the EPUB/PDF to audiobook pipeline."""

    def __init__(
        self,
        input_path: str,
        output_dir: Optional[str] = None,
        config_path: Optional[str] = None,
        voice: str = DEFAULT_VOICE,
        instructions: Optional[str] = None,
        dry_run: bool = False,
        ocr_enabled: bool = True
    ):
        self.input_path = Path(input_path)
        self.config_path = config_path
        self.voice = voice
        self.instructions = instructions
        self.dry_run = dry_run
        self.ocr_enabled = ocr_enabled

        # Detect file format
        self.file_format = self.input_path.suffix.lower()
        if self.file_format not in SUPPORTED_FORMATS:
            raise ValueError(
                f"Unsupported file format: {self.file_format}. "
                f"Supported: {', '.join(SUPPORTED_FORMATS)}"
            )

        # Set up output directory
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path(__file__).parent / "audiobooks"
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Temp directory for intermediate files
        self.temp_dir = Path(__file__).parent / "temp"
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Load configuration
        self.config = self._load_config()

        # Apply config overrides
        self._apply_config_overrides()

        # Initialize the appropriate parser
        if self.file_format == '.epub':
            self.parser = EPUBParser(str(self.input_path))
        else:  # .pdf
            self.parser = PDFParser(str(self.input_path), ocr_enabled=ocr_enabled)

        self.chunker = TokenAwareChunker(max_tokens=1500)
        self.tts_client: Optional[TTSClient] = None
        self.assembler: Optional[AudioAssembler] = None
        self.cost_estimator = CostEstimator()

        # Book name for output files
        self.book_name = self.input_path.stem.replace(' ', '_')

        # Shutdown handling
        self._shutdown_requested = False
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _load_config(self) -> Dict:
        """Load YAML configuration file."""
        config = {}

        if self.config_path and Path(self.config_path).exists():
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}
            print(f"[*] Loaded config: {self.config_path}")

        return config

    def _apply_config_overrides(self) -> None:
        """Apply configuration overrides from YAML."""
        # Voice settings
        voice_config = self.config.get('voice', {})
        if not self.instructions and voice_config.get('instruct'):
            self.instructions = voice_config['instruct']

        # Output settings
        output_config = self.config.get('output', {})
        self.output_format = output_config.get('format', 'm4b')
        self.bitrate = output_config.get('bitrate', DEFAULT_BITRATE)
        self.embed_cover = output_config.get('embed_cover', True)

        # Conversion settings
        conv_config = self.config.get('conversion', {})
        self.announce_chapters = conv_config.get('announce_chapters', True)
        self.chapter_pause = conv_config.get('chapter_pause', DEFAULT_CHUNK_PAUSE)

        # Text cleaning
        self.text_cleaning = self.config.get('text_cleaning', {})

        # Chapter filtering
        chapters_config = self.config.get('chapters', {})
        self.include_chapters = chapters_config.get('include')
        self.exclude_chapters = chapters_config.get('exclude')

        # Special text
        self.intro_text = self.config.get('intro_text')
        self.outro_text = self.config.get('outro_text')
        self.title_announcement = self.config.get('title_announcement')

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signal gracefully."""
        print("\n[!] Shutdown requested - saving progress...")
        self._shutdown_requested = True

    def convert(self) -> Optional[str]:
        """
        Run the full conversion pipeline.

        Returns:
            Path to output file if successful, None otherwise.
        """
        print("=" * 60)
        print("OpenAI Audiobook Converter")
        print("=" * 60)
        print(f"Input: {self.input_path}")
        print(f"Format: {self.file_format.upper()[1:]}")
        print(f"Voice: {self.voice}")
        if self.instructions:
            print(f"Instructions: {self.instructions[:50]}...")
        if self.file_format == '.pdf':
            print(f"OCR Enabled: {self.ocr_enabled}")
        print()

        # Step 1: Parse input file
        print(f"[1/6] Parsing {self.file_format.upper()[1:]}...")

        if self.file_format == '.epub':
            book = self.parser.parse(
                include_ids=self.include_chapters,
                exclude_ids=self.exclude_chapters,
                text_cleaning=self.text_cleaning
            )
        else:  # PDF
            # For PDF, include/exclude are page numbers, not IDs
            include_pages = None
            exclude_pages = None
            if self.include_chapters:
                # Convert to int page numbers if they look like numbers
                try:
                    include_pages = [int(x) for x in self.include_chapters]
                except (ValueError, TypeError):
                    pass
            if self.exclude_chapters:
                try:
                    exclude_pages = [int(x) for x in self.exclude_chapters]
                except (ValueError, TypeError):
                    pass

            book = self.parser.parse(
                include_pages=include_pages,
                exclude_pages=exclude_pages,
                text_cleaning=self.text_cleaning
            )
        print(f"      Found {len(book.chapters)} chapters, {book.total_words:,} words")

        # Step 2: Estimate cost
        print("\n[2/6] Estimating cost...")
        cost_estimate = self.cost_estimator.estimate_book(
            book,
            intro_text=self.intro_text,
            outro_text=self.outro_text,
            title_announcement=self.title_announcement,
            announce_chapters=self.announce_chapters
        )
        print(cost_estimate.display())

        # If dry run, stop here
        if self.dry_run:
            print("\n[DRY RUN] Stopping before conversion.")
            self._show_chapter_list(book)
            return None

        # Step 3: Confirm with user
        print("\nProceed with conversion? [y/N] ", end="")
        response = input().strip().lower()
        if response not in ('y', 'yes'):
            print("[*] Conversion cancelled.")
            return None

        # Step 4: Initialize components
        print("\n[3/6] Initializing TTS client...")
        self.tts_client = TTSClient(
            voice=self.voice,
            instructions=self.instructions,
            response_format="mp3"
        )
        self.assembler = AudioAssembler(self.temp_dir)

        # Step 5: Set up progress tracking
        voice_slug = self.config.get('voice', {}).get('slug', self.voice)
        output_path = self.output_dir / f"{self.book_name}_{voice_slug}.m4b"

        progress_mgr = ProgressManager(
            self.output_dir,
            self.book_name,
            voice_slug
        )
        state = progress_mgr.initialize(
            epub_path=str(self.input_path),
            output_path=str(output_path),
            config_path=self.config_path,
            voice=self.voice,
            instructions=self.instructions,
            chapters_total=len(book.chapters) + 3,  # +3 for intro/title/outro
            total_characters=cost_estimate.total_characters + cost_estimate.additional_chars,
            estimated_cost_usd=cost_estimate.total_cost
        )

        # Step 6: Generate audio
        print("\n[4/6] Generating audio...")
        chapter_audio_files = {}
        chapter_titles = {}
        chapter_order = []

        # Generate intro
        if self.intro_text and not state.is_chapter_complete("_intro"):
            print("  [*] Generating intro...")
            intro_path = self._generate_audio("_intro", self.intro_text)
            if intro_path:
                progress_mgr.mark_chapter_complete("_intro", intro_path, len(self.intro_text))
                chapter_audio_files["_intro"] = intro_path
                chapter_titles["_intro"] = "Introduction"
        elif state.get_cached_audio("_intro"):
            chapter_audio_files["_intro"] = state.get_cached_audio("_intro")
            chapter_titles["_intro"] = "Introduction"

        if "_intro" in chapter_audio_files:
            chapter_order.append("_intro")

        # Generate title announcement
        if self.title_announcement and not state.is_chapter_complete("_title"):
            print("  [*] Generating title announcement...")
            title_path = self._generate_audio("_title", self.title_announcement)
            if title_path:
                progress_mgr.mark_chapter_complete("_title", title_path, len(self.title_announcement))
                chapter_audio_files["_title"] = title_path
                chapter_titles["_title"] = "Title"
        elif state.get_cached_audio("_title"):
            chapter_audio_files["_title"] = state.get_cached_audio("_title")
            chapter_titles["_title"] = "Title"

        if "_title" in chapter_audio_files:
            chapter_order.append("_title")

        # Generate chapter audio
        for i, chapter in enumerate(tqdm(book.chapters, desc="  Chapters")):
            if self._shutdown_requested:
                print("\n[!] Shutdown requested - progress saved")
                progress_mgr.save()
                return None

            # Check if already completed
            if state.is_chapter_complete(chapter.id):
                cached = state.get_cached_audio(chapter.id)
                if cached:
                    chapter_audio_files[chapter.id] = cached
                    chapter_titles[chapter.id] = chapter.title
                    chapter_order.append(chapter.id)
                    continue

            # Generate chapter audio
            chapter_path = self._generate_chapter_audio(chapter, i + 1, len(book.chapters))
            if chapter_path:
                progress_mgr.mark_chapter_complete(chapter.id, chapter_path, chapter.char_count)
                chapter_audio_files[chapter.id] = chapter_path
                chapter_titles[chapter.id] = chapter.title
                chapter_order.append(chapter.id)
            else:
                print(f"\n  [!] Failed to generate audio for: {chapter.title}")

        # Generate outro
        if self.outro_text and not state.is_chapter_complete("_outro"):
            print("  [*] Generating outro...")
            outro_path = self._generate_audio("_outro", self.outro_text)
            if outro_path:
                progress_mgr.mark_chapter_complete("_outro", outro_path, len(self.outro_text))
                chapter_audio_files["_outro"] = outro_path
                chapter_titles["_outro"] = "Closing"
        elif state.get_cached_audio("_outro"):
            chapter_audio_files["_outro"] = state.get_cached_audio("_outro")
            chapter_titles["_outro"] = "Closing"

        if "_outro" in chapter_audio_files:
            chapter_order.append("_outro")

        # Step 7: Assemble audiobook
        print("\n[5/6] Assembling audiobook...")

        # Extract cover (only available for EPUB)
        cover_path = None
        if self.embed_cover and self.file_format == '.epub':
            cover_path = self.parser.extract_cover_to_file(self.temp_dir)
            if cover_path:
                print(f"      Cover extracted: {cover_path.name}")
        elif self.embed_cover and self.file_format == '.pdf':
            print("      Note: Cover extraction not available for PDF files")

        # Build metadata
        metadata = {
            "title": book.metadata.title,
            "author": book.metadata.author,
            "album": book.metadata.title,
            "genre": "Audiobook",
            "year": str(datetime.now().year)
        }

        # Build audio segments
        segments = []
        for chapter_id in chapter_order:
            if chapter_id not in chapter_audio_files:
                continue

            segments.append(AudioSegment(
                path=chapter_audio_files[chapter_id],
                chapter_id=chapter_id,
                chapter_title=chapter_titles.get(chapter_id, chapter_id)
            ))

        # Create M4B
        success = self.assembler.create_m4b(
            segments,
            str(output_path),
            metadata,
            str(cover_path) if cover_path else None,
            self.bitrate
        )

        if success:
            progress_mgr.mark_completed()
            print("\n[6/6] Cleanup...")
            # Keep progress file for reference, clean temp files
            self.assembler.cleanup()

            print("\n" + "=" * 60)
            print("CONVERSION COMPLETE")
            print("=" * 60)
            print(f"Output: {output_path}")
            print(f"Size: {output_path.stat().st_size / (1024*1024):.1f} MB")
            print("=" * 60)

            return str(output_path)
        else:
            print("\n[!] Failed to create M4B file")
            return None

    def _generate_audio(self, segment_id: str, text: str) -> Optional[str]:
        """Generate audio for a text segment."""
        output_path = self.temp_dir / f"{segment_id}.mp3"

        if self.tts_client.generate_speech(text, output_path):
            return str(output_path)
        return None

    def _generate_chapter_audio(
        self,
        chapter: Chapter,
        chapter_num: int,
        total_chapters: int
    ) -> Optional[str]:
        """Generate audio for a complete chapter."""
        # Chunk the chapter text
        chunks = self.chunker.chunk_text(chapter.content)

        # Optionally prepend chapter announcement
        if self.announce_chapters:
            announcement = f"{chapter.title}."
            chunks.insert(0, announcement)

        # Generate audio for each chunk
        chunk_files = []
        for i, chunk in enumerate(chunks):
            chunk_path = self.temp_dir / f"{chapter.id}_chunk_{i:04d}.mp3"

            success = self.tts_client.generate_speech(chunk, chunk_path)
            if success:
                chunk_files.append(str(chunk_path))
            else:
                print(f"\n    [!] Failed chunk {i+1}/{len(chunks)}")
                # Continue with remaining chunks

        if not chunk_files:
            return None

        # Concatenate chunks into chapter audio
        chapter_path = self.temp_dir / f"{chapter.id}.mp3"
        if self.assembler.concatenate_audio(chunk_files, str(chapter_path)):
            # Clean up chunk files
            for f in chunk_files:
                Path(f).unlink(missing_ok=True)
            return str(chapter_path)

        return None

    def _show_chapter_list(self, book: ParsedBook) -> None:
        """Display list of chapters for dry run."""
        print("\nChapters to convert:")
        print("-" * 50)
        for i, ch in enumerate(book.chapters, 1):
            title = ch.title[:40] + "..." if len(ch.title) > 40 else ch.title
            print(f"  {i:2}. {title:<45} ({ch.word_count:,} words)")
        print("-" * 50)
        print(f"Total: {len(book.chapters)} chapters, {book.total_words:,} words")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Convert EPUB/PDF to audiobook using OpenAI TTS",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python convert.py --input book.epub --config chapters.yaml
  python convert.py --input book.pdf --voice coral --dry-run
  python convert.py --input book.pdf --no-ocr  # Skip OCR for PDFs
  python convert.py --epub book.epub --voice coral  # Legacy syntax
        """
    )

    # Input file - support both --input and --epub for backwards compatibility
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input", "-i",
        help="Path to EPUB or PDF file"
    )
    input_group.add_argument(
        "--epub", "-e",
        help="Path to EPUB file (legacy, use --input instead)"
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to YAML config file"
    )
    parser.add_argument(
        "--output", "-o",
        help="Output directory (default: ./audiobooks)"
    )
    parser.add_argument(
        "--voice", "-v",
        default=DEFAULT_VOICE,
        choices=AVAILABLE_VOICES,
        help=f"TTS voice to use (default: {DEFAULT_VOICE})"
    )
    parser.add_argument(
        "--instructions",
        help="Voice style instructions (e.g., 'Speak slowly and clearly')"
    )
    parser.add_argument(
        "--dry-run", "-n",
        action="store_true",
        help="Show cost estimate without converting"
    )
    parser.add_argument(
        "--no-ocr",
        action="store_true",
        help="Disable OCR for PDF files (faster but may miss scanned pages)"
    )
    parser.add_argument(
        "--list-chapters",
        action="store_true",
        help="List all chapters/pages and exit"
    )

    args = parser.parse_args()

    # Get input file path (support both --input and --epub)
    input_path = args.input or args.epub
    file_ext = Path(input_path).suffix.lower()

    # List chapters/pages mode
    if args.list_chapters:
        if file_ext == '.epub':
            epub_parser = EPUBParser(input_path)
            items = epub_parser.list_all_items()
            print(f"\nChapters in {input_path}:\n")
            print(f"{'ID':<25} {'Title':<40} Words")
            print("-" * 75)
            for item_id, title, words in items:
                title_display = title[:37] + "..." if len(title) > 37 else title
                print(f"{item_id:<25} {title_display:<40} {words:,}")
        else:  # PDF
            pdf_parser = PDFParser(input_path, ocr_enabled=False)
            # Show TOC if available
            toc = pdf_parser.get_toc()
            if toc:
                print(f"\nTable of Contents in {input_path}:\n")
                print(f"{'Level':<8} {'Title':<50} Page")
                print("-" * 70)
                for level, title, page in toc:
                    indent = "  " * (level - 1)
                    title_display = title[:47-len(indent)] + "..." if len(title) > 47-len(indent) else title
                    print(f"{level:<8} {indent}{title_display:<50} {page}")

            # Show page summary
            pages = pdf_parser.list_all_pages()
            print(f"\nPages ({len(pages)} total):\n")
            print(f"{'Page':<8} {'Words':<10} Preview")
            print("-" * 70)
            for page_num, words, preview in pages[:20]:  # Show first 20
                print(f"{page_num:<8} {words:<10} {preview}")
            if len(pages) > 20:
                print(f"... and {len(pages) - 20} more pages")
        sys.exit(0)

    # Run conversion
    converter = AudiobookConverter(
        input_path=input_path,
        output_dir=args.output,
        config_path=args.config,
        voice=args.voice,
        instructions=args.instructions,
        dry_run=args.dry_run,
        ocr_enabled=not args.no_ocr
    )

    result = converter.convert()
    sys.exit(0 if result else 1)


if __name__ == "__main__":
    main()
