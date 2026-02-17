"""URL content fetching and extraction service."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional
from urllib.parse import urlparse

import httpx
from bs4 import BeautifulSoup


@dataclass
class URLContent:
    """Extracted content from a URL."""

    title: str
    content: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    word_count: int = 0
    url: str = ""

    def estimate_duration(self, words_per_minute: int = 150) -> float:
        """Estimate audio duration in minutes."""
        return self.word_count / words_per_minute if words_per_minute > 0 else 0.0


@dataclass
class SummaryResult:
    """Structured summary output."""

    summary: str
    insights: list[str]
    takeaways: str
    formatted_text: str


class URLFetcher:
    """Fetches and extracts article-like content from URLs."""

    USER_AGENT = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    MAX_CONTENT_SIZE = 12 * 1024 * 1024
    TIMEOUT = 25.0
    MIN_MEANINGFUL_WORDS = 120

    async def fetch(self, url: str) -> URLContent:
        """Fetch and extract content from a URL.

        Strategy:
        1) Direct HTML fetch + extraction
        2) If sparse (JS-heavy pages), fallback to r.jina.ai mirror extraction
        """
        normalized = self._normalize_url(url)

        html = await self._fetch_text(normalized)
        extracted = self._extract_from_html(html, normalized)

        if extracted.word_count < self.MIN_MEANINGFUL_WORDS:
            mirror = await self._fetch_with_jina(normalized)
            if mirror and mirror.word_count > extracted.word_count:
                extracted = mirror

        if extracted.word_count < 40:
            raise ValueError(
                "Could not extract enough readable text from URL. "
                "The page may require login, heavy JavaScript, or block crawlers."
            )

        return extracted

    def _normalize_url(self, url: str) -> str:
        parsed = urlparse(url)
        if not parsed.scheme:
            url = f"https://{url}"
            parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise ValueError("Invalid URL provided")
        return url

    async def _fetch_text(self, url: str) -> str:
        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(
            headers=headers,
            timeout=self.TIMEOUT,
            follow_redirects=True,
        ) as client:
            try:
                response = await client.get(url)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                raise ValueError(f"Failed to fetch URL: HTTP {e.response.status_code}") from e
            except Exception as e:
                raise ValueError(f"Failed to fetch URL: {e}") from e

        if len(response.content) > self.MAX_CONTENT_SIZE:
            raise ValueError("Page content is too large to process")

        return response.text

    async def _fetch_with_jina(self, url: str) -> Optional[URLContent]:
        """Fallback fetch for JS-heavy pages using jina.ai reader mirror."""
        parsed = urlparse(url)
        target = f"{parsed.netloc}{parsed.path or ''}"
        if parsed.query:
            target += f"?{parsed.query}"
        mirror_url = f"https://r.jina.ai/http://{target}"

        headers = {
            "User-Agent": self.USER_AGENT,
            "Accept": "text/plain, text/markdown;q=0.9, */*;q=0.8",
        }

        try:
            async with httpx.AsyncClient(
                headers=headers,
                timeout=self.TIMEOUT,
                follow_redirects=True,
            ) as client:
                response = await client.get(mirror_url)
                response.raise_for_status()
                raw = response.text
        except Exception:
            return None

        if not raw or len(raw) < 200:
            return None

        title = self._extract_field(raw, "Title:") or "Untitled"
        published = self._extract_field(raw, "Published Time:")

        marker = "Markdown Content:"
        idx = raw.find(marker)
        markdown_body = raw[idx + len(marker) :].strip() if idx >= 0 else raw
        text = self._markdown_to_text(markdown_body)
        text = self._clean_text(text)

        words = len(text.split())
        if words < 40:
            return None

        return URLContent(
            title=title,
            content=text,
            author=None,
            published_date=published,
            word_count=words,
            url=url,
        )

    def _extract_field(self, text: str, field_name: str) -> Optional[str]:
        for line in text.splitlines()[:20]:
            if line.startswith(field_name):
                return line[len(field_name) :].strip()
        return None

    def _extract_from_html(self, html: str, url: str) -> URLContent:
        soup = BeautifulSoup(html, "html.parser")

        title = self._extract_title(soup)
        author = self._extract_author(soup)
        published_date = self._extract_date(soup)

        content = self._extract_article_body(soup)
        if not content:
            content = self._extract_json_ld_article(soup)

        content = self._clean_text(content)
        word_count = len(content.split())

        return URLContent(
            title=title,
            content=content,
            author=author,
            published_date=published_date,
            word_count=word_count,
            url=url,
        )

    def _extract_title(self, soup: BeautifulSoup) -> str:
        meta = soup.find("meta", property="og:title") or soup.find(
            "meta", attrs={"name": "twitter:title"}
        )
        if meta and meta.get("content"):
            return meta["content"].strip()

        for selector in (
            "h1.article-title",
            "h1.entry-title",
            "h1.post-title",
            "article h1",
            "main h1",
            "h1",
        ):
            node = soup.select_one(selector)
            if node:
                txt = node.get_text(" ", strip=True)
                if txt:
                    return txt

        node = soup.find("title")
        return node.get_text(" ", strip=True) if node else "Untitled"

    def _extract_author(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in (
            '[name="author"]',
            '[property="article:author"]',
            ".author",
            ".byline",
            "[rel='author']",
        ):
            node = soup.select_one(selector)
            if not node:
                continue
            txt = node.get("content") if node.name == "meta" else node.get_text(" ", strip=True)
            if txt:
                return txt.strip()
        return None

    def _extract_date(self, soup: BeautifulSoup) -> Optional[str]:
        for selector in (
            '[property="article:published_time"]',
            '[property="og:published_time"]',
            '[name="date"]',
            '[name="datePublished"]',
            "time",
        ):
            node = soup.select_one(selector)
            if not node:
                continue
            if node.name == "time":
                return (node.get("datetime") or node.get_text(" ", strip=True) or None)
            return node.get("content")
        return None

    def _extract_article_body(self, soup: BeautifulSoup) -> str:
        for tag in soup(["script", "style", "noscript", "svg", "canvas", "iframe"]):
            tag.decompose()

        for selector in (
            "article",
            "main",
            "[role='main']",
            ".article-content",
            ".entry-content",
            ".post-content",
            ".markdown-body",
            "#content",
            ".content",
        ):
            node = soup.select_one(selector)
            text = self._text_from_node(node)
            if text and len(text.split()) >= 80:
                return text

        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if p.get_text(" ", strip=True)
        ]
        if len(paragraphs) >= 3:
            return "\n\n".join(paragraphs)

        body = soup.find("body")
        return self._text_from_node(body)

    def _extract_json_ld_article(self, soup: BeautifulSoup) -> str:
        scripts = soup.find_all("script", attrs={"type": "application/ld+json"})
        chunks: list[str] = []
        for script in scripts:
            raw = script.string or script.get_text()
            if not raw:
                continue
            try:
                data = json.loads(raw)
            except Exception:
                continue
            for item in self._iter_json_nodes(data):
                if isinstance(item, dict):
                    article_body = item.get("articleBody")
                    if isinstance(article_body, str) and article_body.strip():
                        chunks.append(article_body.strip())
        return "\n\n".join(chunks)

    def _iter_json_nodes(self, obj):
        if isinstance(obj, list):
            for item in obj:
                yield from self._iter_json_nodes(item)
        elif isinstance(obj, dict):
            yield obj
            for v in obj.values():
                yield from self._iter_json_nodes(v)

    def _text_from_node(self, node: Optional[BeautifulSoup]) -> str:
        if not node:
            return ""
        return node.get_text("\n", strip=True)

    def _markdown_to_text(self, md: str) -> str:
        text = md
        # Split adjacent markdown links onto separate lines first
        text = re.sub(r"\)\s*\[", ")\n[", text)
        # Remove images, keep link text
        text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", "", text)
        text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
        # Remove markdown markers
        text = re.sub(r"^#{1,6}\s*", "", text, flags=re.MULTILINE)
        text = re.sub(r"^\s*[-*+]\s+", "- ", text, flags=re.MULTILINE)
        text = re.sub(r"`{1,3}", "", text)
        text = text.replace("**", "")
        text = text.replace("__", "")
        # Drop markdown table rows/separators (too noisy for TTS)
        lines = []
        for line in text.splitlines():
            if line.count("|") >= 3:
                continue
            if re.match(r"^\s*\|.*\|\s*$", line):
                continue
            if re.match(r"^\s*[:\-\|\s]+$", line):
                continue
            lines.append(line)
        return "\n".join(lines)

    def _clean_text(self, text: str) -> str:
        text = text or ""
        text = text.replace("\r", "\n")
        # Remove common leading nav-link blobs in mirrored markdown pages
        text = re.sub(
            r"^[A-Za-z][A-Za-z0-9+\-]*(?:\s+[A-Za-z][A-Za-z0-9+\-]*){4,}\s{2,}",
            "",
            text,
            count=1,
        )
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)

        bad_prefixes = (
            "Share this article",
            "Read more",
            "Related articles",
            "Follow us",
        )
        lines = []
        seen_real_paragraph = False
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped:
                lines.append("")
                continue
            if any(stripped.lower().startswith(p.lower()) for p in bad_prefixes):
                continue

            tokens = stripped.split()
            punct_ratio = sum(1 for c in stripped if c in ".,;:!?") / max(len(stripped), 1)

            # Drop short nav/link lines at the beginning before real paragraphs start
            if not seen_real_paragraph:
                if len(stripped) < 45 and punct_ratio < 0.01 and len(tokens) <= 4:
                    continue
                if len(stripped) >= 60 or punct_ratio >= 0.01:
                    seen_real_paragraph = True

            # Filter nav-like lines made of many short title-case/all-caps tokens
            if len(tokens) >= 5 and all(len(t) <= 16 for t in tokens):
                upper_ratio = sum(1 for t in tokens if t.isupper()) / len(tokens)
                title_ratio = sum(1 for t in tokens if t[:1].isupper()) / len(tokens)
                if (upper_ratio > 0.4 and punct_ratio < 0.01) or (
                    title_ratio > 0.8 and punct_ratio < 0.01 and len(stripped) <= 140
                ):
                    continue
            lines.append(stripped)

        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()


class ContentProcessor:
    """Processes extracted URL content for audio workflows."""

    @staticmethod
    def create_full_reading(content: URLContent) -> str:
        parts = []
        if content.title:
            parts.append(content.title)
            parts.append("")
        if content.author:
            byline = f"By {content.author}"
            if content.published_date:
                byline += f". Published {content.published_date}."
            parts.append(byline)
            parts.append("")
        parts.append(content.content)
        return "\n".join(parts).strip()

    @staticmethod
    def summarize_with_insights(title: str, text: str) -> SummaryResult:
        sentences = [
            s.strip()
            for s in re.split(r"(?<=[.!?])\s+", text)
            if len(s.strip()) >= 30
        ]

        summary_sentences = sentences[:6]
        if not summary_sentences:
            summary_sentences = [text[:500].strip()] if text.strip() else ["No content extracted."]
        summary = " ".join(summary_sentences)

        insight_keywords = (
            "important",
            "key",
            "significant",
            "impact",
            "means",
            "therefore",
            "however",
            "reveals",
            "shows",
            "future",
        )
        insights = []
        for s in sentences:
            if any(k in s.lower() for k in insight_keywords):
                insights.append(s)
            if len(insights) == 4:
                break
        if len(insights) < 3:
            fillers = [s for s in sentences[6:16] if s not in insights]
            insights.extend(fillers[: 3 - len(insights)])
        insights = insights[:4] if insights else ["The article highlights several notable points."]

        takeaways = (
            "Review the key insights and apply the most relevant ideas to your goals or workflow."
        )

        blocks = [
            f"Summary and insights for: {title or 'Article'}",
            "",
            "Summary:",
            summary,
            "",
            "Key insights:",
        ]
        blocks.extend([f"{i + 1}. {insight}" for i, insight in enumerate(insights)])
        blocks.extend(["", "Takeaway:", takeaways])

        formatted = "\n".join(blocks).strip()

        return SummaryResult(
            summary=summary,
            insights=insights,
            takeaways=takeaways,
            formatted_text=formatted,
        )

    @staticmethod
    def format_for_audio(text: str) -> str:
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


url_fetcher = URLFetcher()
content_processor = ContentProcessor()
