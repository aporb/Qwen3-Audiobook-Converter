"""
Token-aware text chunker for OpenAI TTS.

Splits text into chunks that respect:
1. OpenAI's token limits (~4096 max, we use ~3000 for safety)
2. Sentence boundaries (no mid-sentence splits)
3. Paragraph structure where possible
"""

import re
from typing import List, Tuple
import tiktoken


# OpenAI's gpt-4o-mini-tts has a 2000 token input limit
# We use 1500 as a safe threshold to account for tokenization variance
MAX_TOKENS = 1500
TOKENIZER_MODEL = "gpt-4o"  # Use gpt-4o tokenizer (compatible with mini)


class TokenAwareChunker:
    """Splits text into token-safe chunks while preserving sentence boundaries."""

    def __init__(self, max_tokens: int = MAX_TOKENS):
        self.max_tokens = max_tokens
        self.encoding = tiktoken.encoding_for_model(TOKENIZER_MODEL)

    def count_tokens(self, text: str) -> int:
        """Count tokens in a text string."""
        return len(self.encoding.encode(text))

    def split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences, preserving sentence boundaries."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()

        # Split on sentence-ending punctuation followed by space
        # Handles: . ! ? and also abbreviations like "Dr." or "U.S."
        pattern = r'(?<=[.!?])\s+(?=[A-Z"\'])'
        sentences = re.split(pattern, text)

        # Filter empty strings and strip whitespace
        return [s.strip() for s in sentences if s.strip()]

    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks that fit within token limits.

        Returns a list of text chunks, each under max_tokens.
        Maintains sentence boundaries where possible.
        """
        sentences = self.split_into_sentences(text)

        if not sentences:
            return []

        chunks = []
        current_chunk = []
        current_tokens = 0

        for sentence in sentences:
            sentence_tokens = self.count_tokens(sentence)

            # If single sentence exceeds limit, split it further
            if sentence_tokens > self.max_tokens:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split long sentence by clauses/punctuation
                sub_chunks = self._split_long_sentence(sentence)
                chunks.extend(sub_chunks)
                continue

            # Check if adding this sentence would exceed limit
            if current_tokens + sentence_tokens > self.max_tokens:
                # Save current chunk and start new one
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                current_chunk = [sentence]
                current_tokens = sentence_tokens
            else:
                # Add sentence to current chunk
                current_chunk.append(sentence)
                current_tokens += sentence_tokens

        # Don't forget the last chunk
        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks

    def _split_long_sentence(self, sentence: str) -> List[str]:
        """Split an overly long sentence by clause boundaries."""
        # Try splitting on semicolons, colons, em-dashes first
        parts = re.split(r'(?<=[;:—–])\s*', sentence)

        if len(parts) == 1:
            # Try splitting on commas
            parts = re.split(r'(?<=,)\s*', sentence)

        if len(parts) == 1:
            # Last resort: split by word count
            return self._split_by_words(sentence)

        # Reassemble parts into valid chunks
        chunks = []
        current = []
        current_tokens = 0

        for part in parts:
            part_tokens = self.count_tokens(part)

            if part_tokens > self.max_tokens:
                # Part is still too long, split by words
                if current:
                    chunks.append(' '.join(current))
                    current = []
                    current_tokens = 0
                chunks.extend(self._split_by_words(part))
            elif current_tokens + part_tokens > self.max_tokens:
                chunks.append(' '.join(current))
                current = [part]
                current_tokens = part_tokens
            else:
                current.append(part)
                current_tokens += part_tokens

        if current:
            chunks.append(' '.join(current))

        return chunks

    def _split_by_words(self, text: str) -> List[str]:
        """Last-resort splitting: split by approximate word count."""
        words = text.split()

        chunks = []
        current = []
        current_tokens = 0

        for word in words:
            word_tokens = self.count_tokens(word + ' ')

            if current_tokens + word_tokens > self.max_tokens:
                if current:
                    chunks.append(' '.join(current))
                current = [word]
                current_tokens = word_tokens
            else:
                current.append(word)
                current_tokens += word_tokens

        if current:
            chunks.append(' '.join(current))

        return chunks

    def chunk_with_metadata(self, text: str) -> List[Tuple[str, int, int]]:
        """
        Chunk text and return metadata about each chunk.

        Returns: List of (chunk_text, token_count, char_count)
        """
        chunks = self.chunk_text(text)
        return [
            (chunk, self.count_tokens(chunk), len(chunk))
            for chunk in chunks
        ]


def chunk_text(text: str, max_tokens: int = MAX_TOKENS) -> List[str]:
    """Convenience function for simple chunking."""
    chunker = TokenAwareChunker(max_tokens)
    return chunker.chunk_text(text)


def count_tokens(text: str) -> int:
    """Convenience function to count tokens."""
    encoding = tiktoken.encoding_for_model(TOKENIZER_MODEL)
    return len(encoding.encode(text))


def estimate_chunks(text: str, max_tokens: int = MAX_TOKENS) -> int:
    """Estimate number of chunks without actually splitting."""
    total_tokens = count_tokens(text)
    return max(1, (total_tokens + max_tokens - 1) // max_tokens)
