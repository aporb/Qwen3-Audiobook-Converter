"""Casting Director service — GPT-4o powered character detection."""

import json
import logging
import os
from pathlib import Path
from typing import Optional

from backend.engine import extract_text_from_file, split_into_chunks

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a literary analyst. Given a text excerpt, identify all named characters who have dialogue.
For each character, provide:
- name: The character's name
- description: A brief description (role, personality, age if mentioned)
- sample_lines: 2-3 example dialogue lines they speak

Return a JSON array. Example:
[
  {
    "name": "Alice",
    "description": "Young curious girl, protagonist",
    "sample_lines": ["Curiouser and curiouser!", "Oh dear, I shall be too late!"]
  }
]

Only include characters with actual dialogue. Return empty array if no dialogue found."""


async def analyze_characters(file_path: str, api_key: str | None = None) -> list[dict]:
    """Use GPT-4o to detect characters with dialogue in a book."""
    api_key = api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OpenAI API key required for casting analysis. Enter your key in Settings.")

    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=api_key)

    text = extract_text_from_file(Path(file_path))
    # Sample ~10k chars from the beginning (usually has the most character introductions)
    sample = text[:10_000]

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this text for characters with dialogue:\n\n{sample}"},
        ],
        response_format={"type": "json_object"},
        temperature=0.3,
    )

    content = response.choices[0].message.content or "[]"
    try:
        data = json.loads(content)
        # Handle both {"characters": [...]} and [...] formats
        if isinstance(data, dict):
            characters = data.get("characters", [])
        elif isinstance(data, list):
            characters = data
        else:
            characters = []
    except json.JSONDecodeError:
        characters = []

    return characters
