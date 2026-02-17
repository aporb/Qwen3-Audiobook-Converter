"""Chapter-level text extraction for selective audiobook conversion."""

import re
import zipfile
import xml.etree.ElementTree as ET
from html import unescape
from pathlib import Path

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


def extract_chapter_text(file_path: str, chapter_ids: list[str]) -> str:
    """Extract text from only the specified chapters of a book file.

    Args:
        file_path: Path to the book file (EPUB, PDF, or TXT).
        chapter_ids: List of chapter IDs to include. IDs match those
            returned by extract_book_metadata() — OPF manifest IDs for
            EPUBs, 'page_N' for PDFs, 'full_text' for TXT.

    Returns:
        Concatenated text from the selected chapters.
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    ids_set = set(chapter_ids)

    if ext == ".epub":
        return _extract_epub_chapters(path, ids_set)
    elif ext == ".pdf":
        return _extract_pdf_chapters(path, ids_set)
    else:
        # TXT: single chapter, return everything
        return path.read_text(encoding="utf-8", errors="ignore")


def _extract_epub_chapters(file_path: Path, chapter_ids: set[str]) -> str:
    _NS = {
        'container': 'urn:oasis:names:tc:opendocument:xmlns:container',
        'opf': 'http://www.idpf.org/2007/opf',
    }

    parts: list[str] = []
    with zipfile.ZipFile(str(file_path), 'r') as z:
        # Find OPF
        container = z.read('META-INF/container.xml').decode('utf-8')
        root = ET.fromstring(container)
        rootfile = root.find('.//container:rootfile', _NS)
        opf_path = rootfile.get('full-path')
        opf_dir = str(Path(opf_path).parent)
        if opf_dir == '.':
            opf_dir = ''

        # Parse OPF manifest
        opf_content = z.read(opf_path).decode('utf-8')
        opf_root = ET.fromstring(opf_content)

        manifest = {}
        mf = opf_root.find('opf:manifest', _NS)
        if mf is not None:
            for item in mf.findall('opf:item', _NS):
                manifest[item.get('id')] = item.get('href')

        # Read only matching spine items
        sp = opf_root.find('opf:spine', _NS)
        if sp is not None:
            for itemref in sp.findall('opf:itemref', _NS):
                idref = itemref.get('idref')
                if idref not in chapter_ids:
                    continue
                href = manifest.get(idref)
                if not href:
                    continue
                file_p = f"{opf_dir}/{href}" if opf_dir else href
                try:
                    content = z.read(file_p).decode('utf-8', errors='ignore')
                    clean = _clean_html(content)
                    if clean.strip():
                        parts.append(clean)
                except Exception:
                    pass

    return "\n\n".join(parts)


def _extract_pdf_chapters(file_path: Path, chapter_ids: set[str]) -> str:
    if not _PDF:
        raise ImportError("PyPDF2 required for PDF chapter extraction")

    # chapter_ids are "page_N" strings (1-indexed)
    page_numbers = set()
    for cid in chapter_ids:
        if cid.startswith("page_"):
            try:
                page_numbers.add(int(cid.split("_", 1)[1]))
            except ValueError:
                pass

    parts: list[str] = []
    with open(file_path, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for i, page in enumerate(reader.pages):
            if (i + 1) not in page_numbers:
                continue
            t = page.extract_text()
            if t and t.strip():
                parts.append(t)

    return "\n\n".join(parts)
