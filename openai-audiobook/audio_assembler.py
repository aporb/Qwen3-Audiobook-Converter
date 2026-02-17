"""
Audio assembler for OpenAI Audiobook Converter.

Combines audio chunks into a single audiobook file with chapter markers,
embedded metadata, and optional cover art using FFmpeg.
"""

import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Dict
import shutil


@dataclass
class ChapterMarker:
    """Represents a chapter marker in the audiobook."""
    id: str
    title: str
    start_time: float  # seconds
    end_time: float    # seconds

    @property
    def duration(self) -> float:
        return self.end_time - self.start_time


@dataclass
class AudioSegment:
    """Represents an audio segment to be assembled."""
    path: str
    duration: float = 0.0
    chapter_id: Optional[str] = None
    chapter_title: Optional[str] = None


class AudioAssembler:
    """Assembles audio files into an M4B audiobook with chapters."""

    def __init__(self, temp_dir: Optional[Path] = None):
        """
        Initialize the assembler.

        Args:
            temp_dir: Directory for temporary files (created if not provided)
        """
        self.temp_dir = temp_dir or Path(tempfile.mkdtemp(prefix="audiobook_"))
        self.temp_dir.mkdir(parents=True, exist_ok=True)

        # Check FFmpeg availability
        self._check_ffmpeg()

    def _check_ffmpeg(self) -> None:
        """Check if FFmpeg is available."""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                raise RuntimeError("FFmpeg check failed")
        except FileNotFoundError:
            raise RuntimeError(
                "FFmpeg not found. Please install FFmpeg:\n"
                "  macOS: brew install ffmpeg\n"
                "  Ubuntu: sudo apt-get install ffmpeg"
            )

    def get_audio_duration(self, audio_path: str) -> float:
        """Get duration of an audio file in seconds using FFprobe."""
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path
                ],
                capture_output=True,
                text=True
            )
            return float(result.stdout.strip())
        except (subprocess.CalledProcessError, ValueError):
            return 0.0

    def concatenate_audio(
        self,
        audio_files: List[str],
        output_path: str,
        input_format: str = "mp3"
    ) -> bool:
        """
        Concatenate multiple audio files into one.

        Args:
            audio_files: List of audio file paths in order
            output_path: Output file path
            input_format: Input audio format

        Returns:
            True if successful
        """
        if not audio_files:
            return False

        # Create concat file list
        concat_file = self.temp_dir / "concat_list.txt"
        with open(concat_file, 'w', encoding='utf-8') as f:
            for audio_path in audio_files:
                # Escape single quotes in path
                safe_path = audio_path.replace("'", "'\\''")
                f.write(f"file '{safe_path}'\n")

        # Use FFmpeg concat demuxer
        cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_file),
            "-c", "copy",
            output_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception as e:
            print(f"[!] Concatenation failed: {e}")
            return False

    def create_m4b(
        self,
        audio_files: List[AudioSegment],
        output_path: str,
        metadata: Dict[str, str],
        cover_path: Optional[str] = None,
        bitrate: str = "128k"
    ) -> bool:
        """
        Create M4B audiobook with chapters and metadata.

        Args:
            audio_files: List of AudioSegment objects with chapter info
            output_path: Output M4B file path
            metadata: Dict with title, author, album, etc.
            cover_path: Optional cover image path
            bitrate: Audio bitrate (e.g., "128k")

        Returns:
            True if successful
        """
        if not audio_files:
            return False

        # Step 1: Concatenate all audio files
        concat_output = self.temp_dir / "combined.mp3"
        audio_paths = [seg.path for seg in audio_files]

        print("[*] Concatenating audio files...")
        if not self.concatenate_audio(audio_paths, str(concat_output)):
            print("[!] Failed to concatenate audio files")
            return False

        # Step 2: Calculate chapter timestamps
        chapters = []
        current_time = 0.0

        for seg in audio_files:
            if seg.duration == 0:
                seg.duration = self.get_audio_duration(seg.path)

            if seg.chapter_id and seg.chapter_title:
                chapters.append(ChapterMarker(
                    id=seg.chapter_id,
                    title=seg.chapter_title,
                    start_time=current_time,
                    end_time=current_time + seg.duration
                ))

            current_time += seg.duration

        # Step 3: Create FFMETADATA file
        metadata_file = self._create_ffmetadata(chapters, metadata)

        # Step 4: Build FFmpeg command for M4B creation
        # Note: All inputs must come before mapping options
        cmd = [
            "ffmpeg", "-y",
            "-i", str(concat_output),
            "-i", str(metadata_file),
        ]

        # Add cover image input if provided (before mapping)
        has_cover = cover_path and Path(cover_path).exists()
        if has_cover:
            cmd.extend(["-i", cover_path])

        # Now add mapping options
        cmd.extend([
            "-map", "0:a",
            "-map_metadata", "1",
        ])

        # Add cover mapping if we have a cover
        if has_cover:
            cmd.extend([
                "-map", "2:v",
                "-c:v", "mjpeg",
                "-disposition:v:0", "attached_pic",
            ])

        # Audio encoding
        cmd.extend([
            "-c:a", "aac",
            "-b:a", bitrate,
            output_path
        ])

        print("[*] Creating M4B with chapters...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )
            if result.returncode != 0:
                print(f"[!] FFmpeg error: {result.stderr}")
                return False
            return True
        except Exception as e:
            print(f"[!] M4B creation failed: {e}")
            return False

    def _create_ffmetadata(
        self,
        chapters: List[ChapterMarker],
        metadata: Dict[str, str]
    ) -> Path:
        """Create FFMETADATA file for chapter markers."""
        lines = [";FFMETADATA1"]

        # Add global metadata
        if "title" in metadata:
            lines.append(f"title={self._escape_metadata(metadata['title'])}")
        if "author" in metadata:
            lines.append(f"artist={self._escape_metadata(metadata['author'])}")
        if "album" in metadata:
            lines.append(f"album={self._escape_metadata(metadata['album'])}")
        if "year" in metadata:
            lines.append(f"date={metadata['year']}")
        if "genre" in metadata:
            lines.append(f"genre={self._escape_metadata(metadata['genre'])}")

        # Add chapter markers
        for chapter in chapters:
            start_ms = int(chapter.start_time * 1000)
            end_ms = int(chapter.end_time * 1000)

            lines.append("")
            lines.append("[CHAPTER]")
            lines.append("TIMEBASE=1/1000")
            lines.append(f"START={start_ms}")
            lines.append(f"END={end_ms}")
            lines.append(f"title={self._escape_metadata(chapter.title)}")

        # Write metadata file
        metadata_path = self.temp_dir / "ffmetadata.txt"
        with open(metadata_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return metadata_path

    def _escape_metadata(self, value: str) -> str:
        """Escape special characters in metadata values."""
        # FFmpeg metadata escaping
        value = value.replace("\\", "\\\\")
        value = value.replace("=", "\\=")
        value = value.replace(";", "\\;")
        value = value.replace("#", "\\#")
        value = value.replace("\n", " ")
        return value

    def cleanup(self) -> None:
        """Remove temporary files."""
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)


def assemble_audiobook(
    chapter_audio_files: Dict[str, str],  # chapter_id -> audio_path
    chapter_titles: Dict[str, str],        # chapter_id -> title
    chapter_order: List[str],              # Ordered list of chapter IDs
    output_path: str,
    metadata: Dict[str, str],
    cover_path: Optional[str] = None,
    bitrate: str = "128k"
) -> bool:
    """
    Convenience function to assemble an audiobook from chapter files.

    Args:
        chapter_audio_files: Mapping of chapter ID to audio file path
        chapter_titles: Mapping of chapter ID to display title
        chapter_order: List of chapter IDs in reading order
        output_path: Output M4B file path
        metadata: Book metadata (title, author, etc.)
        cover_path: Optional cover image path
        bitrate: Audio bitrate

    Returns:
        True if successful
    """
    assembler = AudioAssembler()

    # Build AudioSegment list
    segments = []
    for chapter_id in chapter_order:
        if chapter_id not in chapter_audio_files:
            continue

        audio_path = chapter_audio_files[chapter_id]
        if not Path(audio_path).exists():
            print(f"[!] Missing audio file for chapter: {chapter_id}")
            continue

        segments.append(AudioSegment(
            path=audio_path,
            chapter_id=chapter_id,
            chapter_title=chapter_titles.get(chapter_id, chapter_id)
        ))

    if not segments:
        print("[!] No valid audio segments to assemble")
        return False

    try:
        result = assembler.create_m4b(
            segments,
            output_path,
            metadata,
            cover_path,
            bitrate
        )
        return result
    finally:
        assembler.cleanup()
