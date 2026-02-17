"""
EPUB parser for OpenAI Audiobook Converter.

Extracts text content, chapter structure, and metadata from EPUB files.
Compatible with YAML config files from the parent Qwen3-TTS project.
"""

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

import warnings
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

# Suppress XML parsed as HTML warning (common with EPUB content)
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


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
    """Book metadata extracted from EPUB."""
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


class EPUBParser:
    """Parses EPUB files and extracts chapter content."""

    def __init__(self, epub_path: str):
        self.epub_path = Path(epub_path)
        if not self.epub_path.exists():
            raise FileNotFoundError(f"EPUB file not found: {epub_path}")

        self.book: Optional[epub.EpubBook] = None
        self._spine_items: List[Tuple[str, str]] = []  # (id, href)
        self._item_contents: Dict[str, str] = {}
        self._ncx_titles: Dict[str, str] = {}  # href -> title

    def parse(
        self,
        include_ids: Optional[List[str]] = None,
        exclude_ids: Optional[List[str]] = None,
        text_cleaning: Optional[Dict] = None
    ) -> ParsedBook:
        """
        Parse EPUB and extract chapters.

        Args:
            include_ids: If provided, only include these chapter IDs
            exclude_ids: Chapter IDs to exclude (ignored if include_ids is set)
            text_cleaning: Dict of cleaning options (fix_spaced_capitals, etc.)

        Returns:
            ParsedBook with chapters and metadata
        """
        self.book = epub.read_epub(str(self.epub_path))

        # Extract metadata
        metadata = self._extract_metadata()

        # Build spine order
        self._build_spine()

        # Parse NCX for chapter titles
        self._parse_ncx()

        # Extract chapter content
        chapters = []
        for item_id, href in self._spine_items:
            # Apply include/exclude filters
            if include_ids is not None:
                if item_id not in include_ids:
                    continue
            elif exclude_ids is not None:
                if item_id in exclude_ids:
                    continue

            # Get or extract content
            content = self._get_item_content(item_id)
            if not content or len(content.strip()) < 50:
                continue  # Skip empty or very short items

            # Clean the text
            if text_cleaning:
                content = self._clean_text(content, text_cleaning)

            # Get title from NCX or use ID
            title = self._ncx_titles.get(href, item_id)
            title = self._format_chapter_title(title, item_id)

            chapters.append(Chapter(
                id=item_id,
                title=title,
                content=content
            ))

        return ParsedBook(metadata=metadata, chapters=chapters)

    def _extract_metadata(self) -> BookMetadata:
        """Extract book metadata from EPUB."""
        title = "Unknown"
        author = "Unknown"
        language = "en"
        cover_path = None

        if self.book:
            # Title
            titles = self.book.get_metadata('DC', 'title')
            if titles:
                title = titles[0][0]

            # Author
            creators = self.book.get_metadata('DC', 'creator')
            if creators:
                author = creators[0][0]

            # Language
            langs = self.book.get_metadata('DC', 'language')
            if langs:
                language = langs[0][0]

            # Cover image
            cover_path = self._find_cover_image()

        return BookMetadata(
            title=title,
            author=author,
            language=language,
            cover_path=cover_path
        )

    def _find_cover_image(self) -> Optional[str]:
        """Find the cover image in the EPUB."""
        if not self.book:
            return None

        # Try to find cover by metadata reference
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                if 'cover' in item.get_name().lower():
                    return self._extract_cover(item)

        # Try to find by item properties
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                props = getattr(item, 'properties', [])
                if props and 'cover-image' in props:
                    return self._extract_cover(item)

        return None

    def _extract_cover(self, item) -> str:
        """Extract cover image to temp file and return path."""
        # For now, we'll extract covers during assembly
        # Return the item name for reference
        return item.get_name()

    def _build_spine(self) -> None:
        """Build the spine (reading order) from the EPUB."""
        if not self.book:
            return

        self._spine_items = []

        for item_id, linear in self.book.spine:
            item = self.book.get_item_with_id(item_id)
            if item and item.get_type() == ebooklib.ITEM_DOCUMENT:
                href = item.get_name()
                self._spine_items.append((item_id, href))

    def _parse_ncx(self) -> None:
        """Parse NCX navigation for chapter titles."""
        if not self.book:
            return

        self._ncx_titles = {}

        # Find NCX item
        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_NAVIGATION:
                try:
                    ncx_content = item.get_content().decode('utf-8')
                    self._extract_ncx_titles(ncx_content)
                except Exception:
                    pass
                break

    def _extract_ncx_titles(self, ncx_content: str) -> None:
        """Extract titles from NCX XML."""
        try:
            # Parse NCX XML
            root = ET.fromstring(ncx_content)

            # Handle namespace
            ns = {'ncx': 'http://www.daisy.org/z3986/2005/ncx/'}

            # Find all navPoints
            for navpoint in root.findall('.//ncx:navPoint', ns):
                # Get navLabel text
                label = navpoint.find('ncx:navLabel/ncx:text', ns)
                content = navpoint.find('ncx:content', ns)

                if label is not None and content is not None:
                    title = label.text or ""
                    src = content.get('src', '')
                    # Remove anchor from href
                    href = src.split('#')[0]
                    if href:
                        self._ncx_titles[href] = title.strip()

        except ET.ParseError:
            pass

    def _get_item_content(self, item_id: str) -> str:
        """Get the text content of an item by ID."""
        if item_id in self._item_contents:
            return self._item_contents[item_id]

        if not self.book:
            return ""

        item = self.book.get_item_with_id(item_id)
        if not item:
            return ""

        try:
            html_content = item.get_content().decode('utf-8')
            text = self._html_to_text(html_content)
            self._item_contents[item_id] = text
            return text
        except Exception:
            return ""

    def _html_to_text(self, html: str) -> str:
        """Convert HTML to plain text."""
        soup = BeautifulSoup(html, 'lxml')

        # Remove script and style elements
        for tag in soup(['script', 'style', 'head', 'meta', 'link']):
            tag.decompose()

        # Get text
        text = soup.get_text(separator=' ')

        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        return text

    def _clean_text(self, text: str, options: Dict) -> str:
        """Apply text cleaning based on options."""
        if options.get('fix_spaced_capitals', False):
            text = self._fix_spaced_capitals(text)

        if options.get('remove_footnotes', False):
            text = self._remove_footnotes(text)

        if options.get('normalize_special_chars', False):
            text = self._normalize_special_chars(text)

        return text

    def _fix_spaced_capitals(self, text: str) -> str:
        """Fix spaced capital letters like 'A H OUSE' -> 'A House'."""
        # Pattern: sequence of single capitals separated by spaces
        pattern = r'\b([A-Z])\s+([A-Z])\s+([A-Z](?:\s+[A-Z])*)\b'

        def fix_match(m):
            letters = m.group(0).replace(' ', '')
            return letters.title()

        return re.sub(pattern, fix_match, text)

    def _remove_footnotes(self, text: str) -> str:
        """Remove footnote markers."""
        # Remove common footnote markers
        markers = ['*', '†', '‡', '§', '¶', '‖', '**', '***']
        for marker in markers:
            text = text.replace(marker, '')

        # Remove numbered footnote references like [1], [2], etc.
        text = re.sub(r'\[\d+\]', '', text)

        # Clean up extra spaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip()

    def _normalize_special_chars(self, text: str) -> str:
        """Normalize special Unicode characters."""
        replacements = {
            '—': ' - ',  # em-dash
            '–': ' - ',  # en-dash
            '"': '"',    # curly double quote left
            '"': '"',    # curly double quote right
            ''': "'",    # curly single quote left
            ''': "'",    # curly single quote right
            '…': '...',  # ellipsis
            '\u00a0': ' ',  # non-breaking space
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _format_chapter_title(self, title: str, item_id: str) -> str:
        """Format chapter title for announcement."""
        # If title is just the ID or very short, try to make it nicer
        if title == item_id or len(title) < 3:
            # Try to extract chapter number from ID
            match = re.search(r'chapter(\d+)', item_id, re.IGNORECASE)
            if match:
                return f"Chapter {int(match.group(1))}"
            return title.replace('_', ' ').title()

        return title

    def extract_cover_to_file(self, output_path: Path) -> Optional[Path]:
        """Extract cover image to a file."""
        if not self.book:
            return None

        for item in self.book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                name = item.get_name().lower()
                props = getattr(item, 'properties', [])

                if 'cover' in name or (props and 'cover-image' in props):
                    # Determine extension
                    ext = Path(item.get_name()).suffix or '.jpg'
                    cover_file = output_path / f"cover{ext}"

                    with open(cover_file, 'wb') as f:
                        f.write(item.get_content())

                    return cover_file

        return None

    def list_all_items(self) -> List[Tuple[str, str, int]]:
        """List all items in the EPUB for inspection."""
        if not self.book:
            self.book = epub.read_epub(str(self.epub_path))
            self._build_spine()
            self._parse_ncx()

        items = []
        for item_id, href in self._spine_items:
            content = self._get_item_content(item_id)
            title = self._ncx_titles.get(href, item_id)
            word_count = len(content.split()) if content else 0
            items.append((item_id, title, word_count))

        return items


def parse_epub(
    epub_path: str,
    include_ids: Optional[List[str]] = None,
    exclude_ids: Optional[List[str]] = None,
    text_cleaning: Optional[Dict] = None
) -> ParsedBook:
    """Convenience function to parse an EPUB file."""
    parser = EPUBParser(epub_path)
    return parser.parse(include_ids, exclude_ids, text_cleaning)
