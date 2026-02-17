"""
OpenAI TTS Client for audiobook generation.

Wraps OpenAI's audio.speech API with retry logic, error handling,
and progress tracking suitable for long audiobook conversions.
"""

import os
import time
from pathlib import Path
from typing import Optional, Literal

from openai import OpenAI, APIError, RateLimitError, APIConnectionError


# Available voices for gpt-4o-mini-tts
AVAILABLE_VOICES = [
    "alloy", "ash", "ballad", "coral", "echo", "fable",
    "nova", "onyx", "sage", "shimmer", "verse", "marin", "cedar"
]

# Recommended voices for audiobooks
RECOMMENDED_VOICES = ["coral", "onyx", "echo", "marin", "cedar"]

# Output formats
OUTPUT_FORMATS = ["mp3", "opus", "aac", "flac", "wav", "pcm"]

# Default settings
DEFAULT_MODEL = "gpt-4o-mini-tts"
DEFAULT_VOICE = "coral"
DEFAULT_FORMAT = "mp3"
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2  # seconds


class TTSClient:
    """OpenAI TTS API client with retry logic."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
        voice: str = DEFAULT_VOICE,
        response_format: str = DEFAULT_FORMAT,
        instructions: Optional[str] = None
    ):
        """
        Initialize TTS client.

        Args:
            api_key: OpenAI API key (defaults to OPENAI_API_KEY env var)
            model: TTS model to use
            voice: Voice preset to use
            response_format: Audio output format
            instructions: Voice style instructions (for gpt-4o-mini-tts)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "OpenAI API key required. Set OPENAI_API_KEY environment variable "
                "or pass api_key parameter."
            )

        self.client = OpenAI(api_key=self.api_key)
        self.model = model
        self.voice = voice
        self.response_format = response_format
        self.instructions = instructions

        # Validate voice
        if voice not in AVAILABLE_VOICES:
            raise ValueError(
                f"Unknown voice '{voice}'. Available: {', '.join(AVAILABLE_VOICES)}"
            )

    def generate_speech(
        self,
        text: str,
        output_path: Path,
        voice: Optional[str] = None,
        instructions: Optional[str] = None,
        max_retries: int = MAX_RETRIES
    ) -> bool:
        """
        Generate speech from text and save to file.

        Args:
            text: Text to convert to speech
            output_path: Path to save audio file
            voice: Override default voice
            instructions: Override default instructions
            max_retries: Number of retry attempts

        Returns:
            True if successful, False otherwise
        """
        voice = voice or self.voice
        instructions = instructions or self.instructions

        for attempt in range(max_retries):
            try:
                # Prepare API call parameters
                params = {
                    "model": self.model,
                    "voice": voice,
                    "input": text,
                    "response_format": self.response_format
                }

                # Add instructions if provided (only for gpt-4o-mini-tts)
                if instructions and "gpt-4o-mini-tts" in self.model:
                    params["instructions"] = instructions

                # Make API call with streaming response
                with self.client.audio.speech.with_streaming_response.create(
                    **params
                ) as response:
                    response.stream_to_file(str(output_path))

                return True

            except RateLimitError as e:
                wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                print(f"  [!] Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)

            except APIConnectionError as e:
                wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                print(f"  [!] Connection error: {e}. Retrying in {wait_time}s...")
                time.sleep(wait_time)

            except APIError as e:
                print(f"  [!] API error: {e}")
                if attempt < max_retries - 1:
                    wait_time = RETRY_DELAY_BASE * (2 ** attempt)
                    print(f"  [!] Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    return False

            except Exception as e:
                print(f"  [!] Unexpected error: {e}")
                return False

        return False

    def generate_speech_batch(
        self,
        chunks: list,
        output_dir: Path,
        prefix: str = "chunk",
        progress_callback=None
    ) -> list:
        """
        Generate speech for multiple text chunks.

        Args:
            chunks: List of text strings to convert
            output_dir: Directory to save audio files
            prefix: Filename prefix for chunks
            progress_callback: Optional callback(current, total, success)

        Returns:
            List of (chunk_index, output_path, success) tuples
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        results = []
        ext = self.response_format

        for i, chunk in enumerate(chunks):
            output_path = output_dir / f"{prefix}_{i:04d}.{ext}"

            success = self.generate_speech(chunk, output_path)
            results.append((i, str(output_path), success))

            if progress_callback:
                progress_callback(i + 1, len(chunks), success)

            # Small delay between chunks to avoid rate limiting
            if success and i < len(chunks) - 1:
                time.sleep(0.5)

        return results


def create_client(
    voice: str = DEFAULT_VOICE,
    instructions: Optional[str] = None,
    response_format: str = DEFAULT_FORMAT
) -> TTSClient:
    """Create a TTS client with common settings."""
    return TTSClient(
        voice=voice,
        instructions=instructions,
        response_format=response_format
    )


def generate_speech_simple(
    text: str,
    output_path: str,
    voice: str = DEFAULT_VOICE,
    instructions: Optional[str] = None
) -> bool:
    """Simple one-shot speech generation."""
    client = create_client(voice=voice, instructions=instructions)
    return client.generate_speech(text, Path(output_path))


def list_voices() -> list:
    """Return list of available voices."""
    return AVAILABLE_VOICES.copy()


def get_recommended_voices() -> list:
    """Return list of recommended voices for audiobooks."""
    return RECOMMENDED_VOICES.copy()
