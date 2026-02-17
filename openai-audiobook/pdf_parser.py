"""
PDF parser for OpenAI Audiobook Converter.

Extracts text content from PDF files with OCR fallback for scanned/image pages.
Uses OpenAI Vision API (gpt-4o-mini) when direct text extraction fails.

Compatible with the same ParsedBook interface as epub_parser.py.
"""

import base64
import io
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import fitz  # PyMuPDF

from openai import OpenAI


# Reuse data structures from epub_parser for compatibility
@dataclass
class Chapter:
    """Represents a chapter/section in the book."""
    id: str
    title: str
    content: str
    word_count: int = 0
    char_count: int = 0

    def __post_init__(self):
        if self.content:
            self.word_count = len(self.content.split())
            self.char_count = len(self.content)


@dataclass
class BookMetadata:
    """Book metadata extracted from PDF."""
    title: str = "Unknown"
    author: str = "Unknown"
    language: str = "en"
    cover_path: Optional[str] = None


@dataclass
class ParsedBook:
    """Complete parsed book with chapters and metadata."""
    metadata: BookMetadata
    chapters: List[Chapter] = field(default_factory=list)

    @property
    def total_words(self) -> int:
        return sum(ch.word_count for ch in self.chapters)

    @property
    def total_chars(self) -> int:
        return sum(ch.char_count for ch in self.chapters)


@dataclass
class PageExtractionResult:
    """Result of extracting text from a single page."""
    page_num: int
    text: str
    method: str  # "direct" or "ocr"
    confidence: float  # 0.0 to 1.0


class PDFParser:
    """Parses PDF files with OCR fallback for problematic pages."""

    # OCR settings
    OCR_MODEL = "gpt-4o-mini"
    OCR_MAX_TOKENS = 4096

    def __init__(
        self,
        pdf_path: str,
        openai_api_key: Optional[str] = None,
        ocr_enabled: bool = True
    ):
        """
        Initialize PDF parser.

        Args:
            pdf_path: Path to PDF file
            openai_api_key: OpenAI API key for OCR (defaults to OPENAI_API_KEY env)
            ocr_enabled: Whether to use OCR for problematic pages
        """
        self.pdf_path = Path(pdf_path)
        if not self.pdf_path.exists():
            raise FileNotFoundError(f"PDF file not found: {pdf_path}")

        self.ocr_enabled = ocr_enabled
        self.openai_client: Optional[OpenAI] = None

        if ocr_enabled:
            api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
            else:
                print("[!] Warning: No OpenAI API key found. OCR will be disabled.")
                self.ocr_enabled = False

        # Statistics
        self.pages_direct = 0
        self.pages_ocr = 0
        self.pages_failed = 0

    def parse(
        self,
        include_pages: Optional[List[int]] = None,
        exclude_pages: Optional[List[int]] = None,
        text_cleaning: Optional[Dict] = None,
        group_by_toc: bool = True
    ) -> ParsedBook:
        """
        Parse PDF and extract chapters.

        Args:
            include_pages: If provided, only include these page numbers (1-indexed)
            exclude_pages: Page numbers to exclude (1-indexed)
            text_cleaning: Dict of cleaning options
            group_by_toc: Whether to use PDF TOC/bookmarks for chapters

        Returns:
            ParsedBook with chapters and metadata
        """
        doc = fitz.open(str(self.pdf_path))

        try:
            # Extract metadata
            metadata = self._extract_metadata(doc)

            # Get table of contents for chapter structure
            toc = doc.get_toc() if group_by_toc else []

            # Extract text from all pages
            page_texts: Dict[int, PageExtractionResult] = {}
            total_pages = len(doc)

            print(f"[*] Extracting text from {total_pages} pages...")

            for page_num in range(total_pages):
                page_idx = page_num + 1  # 1-indexed for user display

                # Apply include/exclude filters
                if include_pages is not None and page_idx not in include_pages:
                    continue
                if exclude_pages is not None and page_idx in exclude_pages:
                    continue

                page = doc[page_num]
                result = self._extract_page_text(page, page_num)

                if result.text.strip():
                    page_texts[page_num] = result

                # Progress indicator
                if (page_num + 1) % 10 == 0:
                    print(f"      Processed {page_num + 1}/{total_pages} pages...")

            # Print extraction statistics
            print(f"      Direct extraction: {self.pages_direct} pages")
            print(f"      OCR extraction: {self.pages_ocr} pages")
            if self.pages_failed > 0:
                print(f"      Failed: {self.pages_failed} pages")

            # Build chapters from TOC or group pages
            if toc and group_by_toc:
                chapters = self._build_chapters_from_toc(doc, toc, page_texts, text_cleaning)
            else:
                chapters = self._build_chapters_simple(page_texts, text_cleaning)

            return ParsedBook(metadata=metadata, chapters=chapters)

        finally:
            doc.close()

    def _extract_metadata(self, doc: fitz.Document) -> BookMetadata:
        """Extract book metadata from PDF."""
        meta = doc.metadata or {}

        title = meta.get("title", "") or self.pdf_path.stem.replace("_", " ")
        author = meta.get("author", "") or "Unknown"

        # Try to extract language (not always available)
        language = "en"  # Default

        return BookMetadata(
            title=title,
            author=author,
            language=language
        )

    def _extract_page_text(
        self,
        page: fitz.Page,
        page_num: int
    ) -> PageExtractionResult:
        """
        Extract text from a single page, using OCR if needed.
        """
        # First, try direct text extraction
        direct_text = page.get_text("text")

        # Check if extraction quality is acceptable
        needs_ocr = self._needs_ocr(direct_text, page)

        if not needs_ocr:
            self.pages_direct += 1
            return PageExtractionResult(
                page_num=page_num,
                text=direct_text,
                method="direct",
                confidence=1.0
            )

        # Try OCR if enabled
        if self.ocr_enabled and self.openai_client:
            ocr_text = self._ocr_page(page, page_num)
            if ocr_text:
                self.pages_ocr += 1
                return PageExtractionResult(
                    page_num=page_num,
                    text=ocr_text,
                    method="ocr",
                    confidence=0.9
                )

        # Fallback to whatever we got from direct extraction
        if direct_text.strip():
            self.pages_direct += 1
            return PageExtractionResult(
                page_num=page_num,
                text=direct_text,
                method="direct",
                confidence=0.5
            )

        self.pages_failed += 1
        return PageExtractionResult(
            page_num=page_num,
            text="",
            method="failed",
            confidence=0.0
        )

    def _needs_ocr(self, text: str, page: fitz.Page) -> bool:
        """
        Determine if a page needs OCR based on text quality.

        This is where we detect problematic extractions:
        - Too little text for page size
        - High ratio of special/garbage characters
        - Text appears garbled or nonsensical

        TODO: Implement your quality detection logic here.
        """
        # Get page dimensions for context
        page_area = page.rect.width * page.rect.height

        # Strip and normalize text
        clean_text = text.strip()

        # Heuristic 1: Empty or very short text for a full page
        if len(clean_text) < 50:
            # Check if page has images (likely scanned)
            images = page.get_images()
            if images:
                return True

        # Heuristic 2: Check character quality
        if clean_text:
            quality_score = self._calculate_text_quality(clean_text)
            if quality_score < 0.6:  # Below 60% quality threshold
                return True

        return False

    def _calculate_text_quality(self, text: str) -> float:
        """
        Calculate a quality score for extracted text.

        Returns a score from 0.0 (garbage) to 1.0 (clean text).

        Factors considered:
        - Ratio of alphanumeric to total characters
        - Presence of common words
        - Absence of garbled character sequences
        """
        if not text:
            return 0.0

        # Count character types
        total_chars = len(text)
        alpha_chars = sum(1 for c in text if c.isalpha())
        digit_chars = sum(1 for c in text if c.isdigit())
        space_chars = sum(1 for c in text if c.isspace())
        punct_chars = sum(1 for c in text if c in '.,;:!?"\'-()[]{}')

        # Calculate ratios
        normal_chars = alpha_chars + digit_chars + space_chars + punct_chars
        normal_ratio = normal_chars / total_chars if total_chars > 0 else 0

        # Check for garbled sequences (e.g., consecutive special chars)
        garbled_pattern = r'[^\w\s.,;:!?"\'\-()[\]{}]{3,}'
        garbled_matches = len(re.findall(garbled_pattern, text))
        garbled_penalty = min(garbled_matches * 0.1, 0.5)

        # Check for common English words (basic sanity check)
        common_words = {'the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'for'}
        words = set(text.lower().split())
        common_count = len(words & common_words)
        common_bonus = min(common_count * 0.05, 0.2)

        # Calculate final score
        score = normal_ratio - garbled_penalty + common_bonus
        return max(0.0, min(1.0, score))

    def _ocr_page(self, page: fitz.Page, page_num: int) -> Optional[str]:
        """
        Use OpenAI Vision API to OCR a page.
        """
        try:
            # Render page to image
            # Using 150 DPI for balance of quality and size
            mat = fitz.Matrix(150/72, 150/72)  # 150 DPI
            pix = page.get_pixmap(matrix=mat)

            # Convert to PNG bytes
            img_bytes = pix.tobytes("png")

            # Encode to base64
            img_base64 = base64.b64encode(img_bytes).decode("utf-8")

            # Call Vision API
            response = self.openai_client.chat.completions.create(
                model=self.OCR_MODEL,
                max_tokens=self.OCR_MAX_TOKENS,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": (
                                    "Extract all the text from this book page. "
                                    "Maintain paragraph structure. "
                                    "Do not include page numbers, headers, or footers. "
                                    "Only output the extracted text, nothing else."
                                )
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/png;base64,{img_base64}",
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ]
            )

            return response.choices[0].message.content

        except Exception as e:
            print(f"      [!] OCR failed for page {page_num + 1}: {e}")
            return None

    def _build_chapters_from_toc(
        self,
        doc: fitz.Document,
        toc: List[Tuple],
        page_texts: Dict[int, PageExtractionResult],
        text_cleaning: Optional[Dict]
    ) -> List[Chapter]:
        """Build chapters based on PDF table of contents."""
        chapters = []

        # TOC format: [(level, title, page_number), ...]
        # We'll use level-1 entries as chapters
        chapter_boundaries = []

        for level, title, page_num in toc:
            if level == 1:  # Top-level chapters
                chapter_boundaries.append((title, page_num - 1))  # Convert to 0-indexed

        if not chapter_boundaries:
            # No top-level entries, use all entries
            for level, title, page_num in toc:
                chapter_boundaries.append((title, page_num - 1))

        # Build chapters from boundaries
        total_pages = len(doc)

        for i, (title, start_page) in enumerate(chapter_boundaries):
            # Determine end page
            if i + 1 < len(chapter_boundaries):
                end_page = chapter_boundaries[i + 1][1]
            else:
                end_page = total_pages

            # Collect text from pages in this range
            chapter_text_parts = []
            for page_num in range(start_page, end_page):
                if page_num in page_texts:
                    chapter_text_parts.append(page_texts[page_num].text)

            content = "\n\n".join(chapter_text_parts)

            if text_cleaning:
                content = self._clean_text(content, text_cleaning)

            if content.strip():
                chapter_id = f"chapter_{i+1:03d}"
                chapters.append(Chapter(
                    id=chapter_id,
                    title=title,
                    content=content.strip()
                ))

        return chapters

    def _detect_chapter_boundaries(
        self,
        page_texts: Dict[int, PageExtractionResult]
    ) -> List[Tuple[int, str]]:
        """
        Detect chapter boundaries by looking for chapter headings in text.

        Returns list of (page_num, chapter_title) tuples.
        Only returns boundaries if confident about the structure.
        """
        # Patterns for clear chapter headings (conservative approach)
        chapter_patterns = [
            # "Chapter 1", "Chapter I", "CHAPTER ONE" - very reliable
            r'^(?:CHAPTER|Chapter)\s+(?:\d+|[IVXLCDM]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten|Eleven|Twelve)(?:\s*[:\.\-].*)?$',
            # "Part I", "Part 1", "PART ONE" - reliable
            r'^(?:PART|Part)\s+(?:\d+|[IVXLCDM]+|One|Two|Three|Four|Five|Six|Seven|Eight|Nine|Ten)(?:\s*[:\.\-].*)?$',
        ]

        # Patterns for front/back matter (only match at exact line start)
        matter_patterns = [
            r'^Introduction$',
            r'^Preface$',
            r'^Foreword$',
            r'^Prologue$',
            r'^Epilogue$',
            r'^Conclusion$',
            r'^Afterword$',
            r'^Appendix(?:\s+[A-Z])?$',
            r'^Bibliography$',
            r'^Notes$',
            r'^Index$',
            r'^Acknowledgements?$',
        ]

        all_patterns = chapter_patterns + matter_patterns
        boundaries = []
        sorted_pages = sorted(page_texts.keys())

        for page_num in sorted_pages:
            text = page_texts[page_num].text
            # Look at the first 300 characters of each page
            page_start = text[:300]

            # Split into lines and check first few non-empty lines
            lines = [l.strip() for l in page_start.split('\n') if l.strip()]

            for line in lines[:3]:
                # Skip very long lines (likely body text, not headers)
                if len(line) > 60:
                    continue

                # Skip lines that look like running headers with page numbers
                if re.match(r'.*\d+\s*$', line) and len(line) < 50:
                    continue

                # Check for chapter patterns
                for pattern in all_patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        title = line.strip()
                        boundaries.append((page_num, title))
                        break
                else:
                    continue
                break  # Found a match, move to next page

        # Deduplicate: keep only first occurrence of each section name
        # (handles cases where "Introduction" or "Index" appears on multiple pages)
        seen_titles = set()
        deduped = []
        for page_num, title in boundaries:
            title_key = title.lower().split()[0] if title else ""  # Use first word as key
            if title_key not in seen_titles:
                seen_titles.add(title_key)
                deduped.append((page_num, title))

        # Only use detected boundaries if we found a reasonable number
        # and chapters are reasonably sized (not one giant chapter)
        if len(deduped) >= 4 and len(deduped) <= len(sorted_pages) // 10:
            return deduped

        return []  # Too few meaningful chapters - fall back to page grouping

    def _build_chapters_simple(
        self,
        page_texts: Dict[int, PageExtractionResult],
        text_cleaning: Optional[Dict]
    ) -> List[Chapter]:
        """Build chapters by detecting headings or grouping pages."""
        sorted_pages = sorted(page_texts.keys())

        # First, try to detect chapter boundaries
        boundaries = self._detect_chapter_boundaries(page_texts)

        if boundaries:
            # Build chapters from detected boundaries
            print(f"      Detected {len(boundaries)} chapter boundaries")
            return self._build_chapters_from_boundaries(
                boundaries, sorted_pages, page_texts, text_cleaning
            )

        # Fallback: group every N pages into a chapter
        print("      No chapter headings detected, using page grouping")
        PAGES_PER_CHAPTER = 20

        chapters = []

        for i in range(0, len(sorted_pages), PAGES_PER_CHAPTER):
            chunk_pages = sorted_pages[i:i + PAGES_PER_CHAPTER]

            chapter_text_parts = []
            for page_num in chunk_pages:
                chapter_text_parts.append(page_texts[page_num].text)

            content = "\n\n".join(chapter_text_parts)

            if text_cleaning:
                content = self._clean_text(content, text_cleaning)

            if content.strip():
                chapter_num = (i // PAGES_PER_CHAPTER) + 1
                start_page = chunk_pages[0] + 1
                end_page = chunk_pages[-1] + 1

                chapters.append(Chapter(
                    id=f"chapter_{chapter_num:03d}",
                    title=f"Pages {start_page}-{end_page}",
                    content=content.strip()
                ))

        return chapters

    def _build_chapters_from_boundaries(
        self,
        boundaries: List[Tuple[int, str]],
        sorted_pages: List[int],
        page_texts: Dict[int, PageExtractionResult],
        text_cleaning: Optional[Dict]
    ) -> List[Chapter]:
        """Build chapters from detected boundaries."""
        chapters = []
        total_pages = max(sorted_pages) + 1 if sorted_pages else 0

        for i, (start_page, title) in enumerate(boundaries):
            # Determine end page
            if i + 1 < len(boundaries):
                end_page = boundaries[i + 1][0]
            else:
                end_page = total_pages

            # Collect text from pages in this range
            chapter_text_parts = []
            for page_num in sorted_pages:
                if start_page <= page_num < end_page:
                    chapter_text_parts.append(page_texts[page_num].text)

            content = "\n\n".join(chapter_text_parts)

            if text_cleaning:
                content = self._clean_text(content, text_cleaning)

            if content.strip():
                chapter_id = f"chapter_{i+1:03d}"
                chapters.append(Chapter(
                    id=chapter_id,
                    title=title,
                    content=content.strip()
                ))

        return chapters

    def _clean_text(self, text: str, options: Dict) -> str:
        """Apply text cleaning based on options."""
        if options.get('fix_spaced_capitals', False):
            text = self._fix_spaced_capitals(text)

        if options.get('remove_footnotes', False):
            text = self._remove_footnotes(text)

        if options.get('normalize_special_chars', False):
            text = self._normalize_special_chars(text)

        if options.get('remove_page_numbers', True):
            text = self._remove_page_numbers(text)

        if options.get('fix_hyphenation', True):
            text = self._fix_hyphenation(text)

        return text

    def _fix_spaced_capitals(self, text: str) -> str:
        """Fix spaced capital letters like 'T H E' -> 'THE'."""
        pattern = r'\b([A-Z])\s+([A-Z])\s+([A-Z](?:\s+[A-Z])*)\b'

        def fix_match(m):
            letters = m.group(0).replace(' ', '')
            return letters.title()

        return re.sub(pattern, fix_match, text)

    def _remove_footnotes(self, text: str) -> str:
        """Remove footnote markers and references."""
        # Remove superscript-style markers
        text = re.sub(r'\[\d+\]', '', text)
        text = re.sub(r'\d+\s*$', '', text, flags=re.MULTILINE)

        # Remove common footnote symbols
        for marker in ['*', '†', '‡', '§', '¶', '‖']:
            text = text.replace(marker, '')

        return re.sub(r'\s+', ' ', text).strip()

    def _normalize_special_chars(self, text: str) -> str:
        """Normalize special Unicode characters."""
        replacements = {
            '—': ' - ',
            '–': ' - ',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
            '…': '...',
            '\u00a0': ' ',
            'ﬁ': 'fi',
            'ﬂ': 'fl',
            'ﬀ': 'ff',
            'ﬃ': 'ffi',
            'ﬄ': 'ffl',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _remove_page_numbers(self, text: str) -> str:
        """Remove standalone page numbers."""
        # Remove lines that are just numbers
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped and not stripped.isdigit():
                cleaned_lines.append(line)
        return '\n'.join(cleaned_lines)

    def _fix_hyphenation(self, text: str) -> str:
        """Fix words split across lines with hyphens."""
        # Match word-ending hyphen followed by newline and word continuation
        return re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)

    def list_all_pages(self) -> List[Tuple[int, int, str]]:
        """List all pages for inspection."""
        doc = fitz.open(str(self.pdf_path))

        try:
            pages = []
            for i, page in enumerate(doc):
                text = page.get_text("text")
                word_count = len(text.split())

                # Get first 50 chars as preview
                preview = text[:50].replace('\n', ' ').strip()
                if len(text) > 50:
                    preview += "..."

                pages.append((i + 1, word_count, preview))

            return pages
        finally:
            doc.close()

    def get_toc(self) -> List[Tuple[int, str, int]]:
        """Get table of contents."""
        doc = fitz.open(str(self.pdf_path))
        try:
            return doc.get_toc()
        finally:
            doc.close()


def parse_pdf(
    pdf_path: str,
    include_pages: Optional[List[int]] = None,
    exclude_pages: Optional[List[int]] = None,
    text_cleaning: Optional[Dict] = None,
    ocr_enabled: bool = True
) -> ParsedBook:
    """Convenience function to parse a PDF file."""
    parser = PDFParser(pdf_path, ocr_enabled=ocr_enabled)
    return parser.parse(include_pages, exclude_pages, text_cleaning)
