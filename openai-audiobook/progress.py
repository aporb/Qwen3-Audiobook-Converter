"""
Progress tracking and resume capability for OpenAI Audiobook Converter.

Manages conversion state via JSON checkpoints, enabling resume of interrupted
conversions without re-processing completed chapters.
"""

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class ConversionState:
    """Tracks conversion progress for checkpoint/resume capability."""

    # Input/output paths
    epub_path: str
    output_path: str
    config_path: Optional[str] = None

    # Voice settings (for verification on resume)
    voice: str = "coral"
    instructions: Optional[str] = None

    # Progress tracking
    chapters_total: int = 0
    chapters_completed: List[str] = field(default_factory=list)
    chapter_audio_files: Dict[str, str] = field(default_factory=dict)

    # Timing and metadata
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed: bool = False

    # Cost tracking
    total_characters: int = 0
    characters_processed: int = 0
    estimated_cost_usd: float = 0.0

    def save(self, path: Path) -> None:
        """Save state to JSON file."""
        self.updated_at = datetime.now().isoformat()
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> 'ConversionState':
        """Load state from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls(**data)

    def mark_chapter_complete(
        self,
        chapter_id: str,
        audio_path: str,
        characters: int = 0
    ) -> None:
        """Mark a chapter as completed and record its audio file."""
        if chapter_id not in self.chapters_completed:
            self.chapters_completed.append(chapter_id)
        self.chapter_audio_files[chapter_id] = audio_path
        self.characters_processed += characters
        self.updated_at = datetime.now().isoformat()

    def is_chapter_complete(self, chapter_id: str) -> bool:
        """Check if a chapter has already been processed."""
        return chapter_id in self.chapters_completed

    def get_cached_audio(self, chapter_id: str) -> Optional[str]:
        """Get the cached audio path for a completed chapter."""
        path = self.chapter_audio_files.get(chapter_id)
        if path and Path(path).exists():
            return path
        return None

    @property
    def progress_percent(self) -> float:
        """Calculate completion percentage."""
        if self.chapters_total == 0:
            return 0.0
        return (len(self.chapters_completed) / self.chapters_total) * 100

    @property
    def remaining_chapters(self) -> int:
        """Get count of remaining chapters."""
        return self.chapters_total - len(self.chapters_completed)


class ProgressManager:
    """Manages conversion progress with automatic checkpointing."""

    def __init__(self, output_dir: Path, book_name: str, voice_slug: str = ""):
        self.output_dir = Path(output_dir)
        self.book_name = book_name
        self.voice_slug = voice_slug

        # Progress file naming: .{book_name}_{voice}.progress.json
        suffix = f"_{voice_slug}" if voice_slug else ""
        self.state_file = self.output_dir / f".{book_name}{suffix}.progress.json"

        self.state: Optional[ConversionState] = None

    def initialize(
        self,
        epub_path: str,
        output_path: str,
        config_path: Optional[str] = None,
        voice: str = "coral",
        instructions: Optional[str] = None,
        chapters_total: int = 0,
        total_characters: int = 0,
        estimated_cost_usd: float = 0.0
    ) -> ConversionState:
        """Initialize or resume conversion state."""

        # Try to load existing state
        if self.state_file.exists():
            try:
                self.state = ConversionState.load(self.state_file)
                print(f"[*] Resuming from checkpoint: {len(self.state.chapters_completed)}/{self.state.chapters_total} chapters done")
                return self.state
            except Exception as e:
                print(f"[!] Could not load progress file: {e}")
                print("[*] Starting fresh conversion")

        # Create new state
        self.state = ConversionState(
            epub_path=epub_path,
            output_path=output_path,
            config_path=config_path,
            voice=voice,
            instructions=instructions,
            chapters_total=chapters_total,
            total_characters=total_characters,
            estimated_cost_usd=estimated_cost_usd
        )
        self.save()
        return self.state

    def save(self) -> None:
        """Save current state to disk."""
        if self.state:
            self.state.save(self.state_file)

    def mark_chapter_complete(
        self,
        chapter_id: str,
        audio_path: str,
        characters: int = 0
    ) -> None:
        """Mark chapter complete and save checkpoint."""
        if self.state:
            self.state.mark_chapter_complete(chapter_id, audio_path, characters)
            self.save()

    def mark_completed(self) -> None:
        """Mark the entire conversion as complete."""
        if self.state:
            self.state.completed = True
            self.save()

    def cleanup(self) -> None:
        """Remove progress file after successful completion."""
        if self.state_file.exists():
            self.state_file.unlink()
            print(f"[*] Removed progress file: {self.state_file.name}")


def get_progress_file_path(output_dir: Path, book_name: str, voice_slug: str = "") -> Path:
    """Get the path to a progress file without creating a manager."""
    suffix = f"_{voice_slug}" if voice_slug else ""
    return output_dir / f".{book_name}{suffix}.progress.json"
