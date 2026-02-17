"""Export service — format conversion and subtitle generation."""

import subprocess
from pathlib import Path

from backend.config import settings


def convert_audio_format(input_path: str, output_format: str) -> str:
    """Convert audio file to a different format using ffmpeg."""
    inp = Path(input_path)
    out_name = inp.stem + f".{output_format}"
    out_path = settings.audio_dir / out_name

    cmd = ["ffmpeg", "-y", "-i", str(inp), str(out_path)]
    subprocess.run(cmd, check=True, capture_output=True)
    return str(out_path)


def generate_srt(text: str, duration_seconds: float, output_path: str) -> str:
    """Generate a basic SRT subtitle file from text and duration."""
    words = text.split()
    total_words = len(words)
    if total_words == 0:
        return output_path

    # Simple proportional timing
    words_per_second = total_words / duration_seconds if duration_seconds > 0 else 10
    chunk_words = max(8, int(words_per_second * 3))  # ~3 seconds per subtitle

    lines = []
    idx = 1
    pos = 0
    while pos < total_words:
        chunk = words[pos : pos + chunk_words]
        start_sec = pos / words_per_second
        end_sec = min((pos + len(chunk)) / words_per_second, duration_seconds)
        lines.append(str(idx))
        lines.append(f"{_fmt_srt_time(start_sec)} --> {_fmt_srt_time(end_sec)}")
        lines.append(" ".join(chunk))
        lines.append("")
        idx += 1
        pos += chunk_words

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    return output_path


def generate_vtt(text: str, duration_seconds: float, output_path: str) -> str:
    """Generate a WebVTT subtitle file."""
    srt_path = output_path.replace(".vtt", ".srt")
    generate_srt(text, duration_seconds, srt_path)
    # Convert SRT to VTT
    srt_content = Path(srt_path).read_text(encoding="utf-8")
    vtt_content = "WEBVTT\n\n" + srt_content.replace(",", ".")
    Path(output_path).write_text(vtt_content, encoding="utf-8")
    Path(srt_path).unlink(missing_ok=True)
    return output_path


def _fmt_srt_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds % 1) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"
