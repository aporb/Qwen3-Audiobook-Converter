"""
Cost estimator for OpenAI TTS API.

Calculates character counts and estimates API costs before conversion,
providing a breakdown by chapter for informed decision-making.
"""

from dataclasses import dataclass
from typing import List, Optional, Dict

from epub_parser import ParsedBook, Chapter


# OpenAI TTS pricing (as of January 2025)
# gpt-4o-mini-tts: $0.015 per 1,000 characters
COST_PER_1K_CHARS = 0.015

# Alternative pricing tiers (for reference)
PRICING = {
    "gpt-4o-mini-tts": 0.015,  # $0.015 per 1K chars
    "tts-1": 0.015,            # $0.015 per 1K chars
    "tts-1-hd": 0.030,         # $0.030 per 1K chars (higher quality)
}


@dataclass
class ChapterCost:
    """Cost estimate for a single chapter."""
    id: str
    title: str
    char_count: int
    word_count: int
    estimated_cost: float


@dataclass
class CostEstimate:
    """Complete cost estimate for book conversion."""
    total_characters: int
    total_words: int
    estimated_cost_usd: float
    chapter_costs: List[ChapterCost]
    model: str = "gpt-4o-mini-tts"

    # Additional text (intro, outro, chapter announcements)
    additional_chars: int = 0
    additional_cost: float = 0.0

    @property
    def total_cost(self) -> float:
        """Total estimated cost including additional text."""
        return self.estimated_cost_usd + self.additional_cost

    def display(self) -> str:
        """Format cost estimate for display."""
        lines = [
            "",
            "=" * 50,
            "COST ESTIMATE",
            "=" * 50,
            f"Model: {self.model}",
            f"Rate: ${PRICING.get(self.model, COST_PER_1K_CHARS):.3f} per 1,000 characters",
            "",
            f"Book content:",
            f"  Characters: {self.total_characters:,}",
            f"  Words: {self.total_words:,}",
            f"  Estimated cost: ${self.estimated_cost_usd:.2f}",
        ]

        if self.additional_chars > 0:
            lines.extend([
                "",
                f"Additional (intro/outro/announcements):",
                f"  Characters: {self.additional_chars:,}",
                f"  Estimated cost: ${self.additional_cost:.2f}",
            ])

        lines.extend([
            "",
            "-" * 50,
            f"TOTAL ESTIMATED COST: ${self.total_cost:.2f} USD",
            "-" * 50,
            "",
            "Chapter breakdown:",
        ])

        for ch in self.chapter_costs:
            title_display = ch.title[:35] + "..." if len(ch.title) > 35 else ch.title
            lines.append(
                f"  {title_display:<40} {ch.char_count:>8,} chars  ${ch.estimated_cost:.2f}"
            )

        lines.append("=" * 50)
        return "\n".join(lines)


class CostEstimator:
    """Estimates OpenAI TTS API costs for book conversion."""

    def __init__(self, model: str = "gpt-4o-mini-tts"):
        self.model = model
        self.rate = PRICING.get(model, COST_PER_1K_CHARS)

    def calculate_cost(self, char_count: int) -> float:
        """Calculate cost for a given character count."""
        return (char_count / 1000) * self.rate

    def estimate_book(
        self,
        book: ParsedBook,
        intro_text: Optional[str] = None,
        outro_text: Optional[str] = None,
        title_announcement: Optional[str] = None,
        announce_chapters: bool = True
    ) -> CostEstimate:
        """
        Estimate full conversion cost for a parsed book.

        Args:
            book: Parsed book with chapters
            intro_text: Intro narration text
            outro_text: Outro narration text
            title_announcement: Book title announcement
            announce_chapters: Whether chapters will be announced

        Returns:
            CostEstimate with detailed breakdown
        """
        chapter_costs = []
        total_chars = 0
        total_words = 0

        for chapter in book.chapters:
            cost = self.calculate_cost(chapter.char_count)
            chapter_costs.append(ChapterCost(
                id=chapter.id,
                title=chapter.title,
                char_count=chapter.char_count,
                word_count=chapter.word_count,
                estimated_cost=cost
            ))
            total_chars += chapter.char_count
            total_words += chapter.word_count

        estimated_cost = self.calculate_cost(total_chars)

        # Calculate additional text costs
        additional_chars = 0
        if intro_text:
            additional_chars += len(intro_text)
        if outro_text:
            additional_chars += len(outro_text)
        if title_announcement:
            additional_chars += len(title_announcement)
        if announce_chapters:
            # Estimate chapter announcement text
            for ch in book.chapters:
                additional_chars += len(ch.title) + 10  # "Chapter: " prefix

        additional_cost = self.calculate_cost(additional_chars)

        return CostEstimate(
            total_characters=total_chars,
            total_words=total_words,
            estimated_cost_usd=estimated_cost,
            chapter_costs=chapter_costs,
            model=self.model,
            additional_chars=additional_chars,
            additional_cost=additional_cost
        )

    def estimate_text(self, text: str) -> float:
        """Estimate cost for a single text string."""
        return self.calculate_cost(len(text))


def estimate_cost(
    book: ParsedBook,
    intro_text: Optional[str] = None,
    outro_text: Optional[str] = None,
    title_announcement: Optional[str] = None,
    announce_chapters: bool = True,
    model: str = "gpt-4o-mini-tts"
) -> CostEstimate:
    """Convenience function to estimate book conversion cost."""
    estimator = CostEstimator(model)
    return estimator.estimate_book(
        book, intro_text, outro_text, title_announcement, announce_chapters
    )


def format_cost(cost: float) -> str:
    """Format a cost value for display."""
    if cost < 0.01:
        return f"${cost:.4f}"
    elif cost < 1.00:
        return f"${cost:.3f}"
    else:
        return f"${cost:.2f}"
