"""AI text cleaning service — cleans extracted text via LLM chat completions."""

from typing import Callable

from openai import OpenAI

from backend.engine import split_into_chunks

PRESET_PROMPTS: dict[str, str] = {
    "ocr_cleanup": (
        "You are a text restoration assistant. Clean the following OCR-extracted text:\n"
        "- Fix OCR errors (e.g. 'rn' misread as 'm', '1' misread as 'l', '0' as 'O')\n"
        "- Normalize paragraph breaks — remove mid-sentence line breaks, preserve paragraph boundaries\n"
        "- Remove headers, footers, and page numbers that were captured during extraction\n"
        "- Fix hyphenation artifacts from line-wrapping (e.g. 're-\\nceive' → 'receive')\n"
        "- Preserve the original meaning, tone, and structure of the text\n"
        "Return ONLY the cleaned text. Do not add commentary or explanation."
    ),
    "tts_optimization": (
        "You are a text-to-speech preparation assistant. Rewrite the following text to be spoken aloud naturally:\n"
        "- Expand abbreviations (e.g. 'Dr.' → 'Doctor', 'St.' → 'Street' or 'Saint' based on context)\n"
        "- Spell out numbers in a speakable way (e.g. '1,234' → 'one thousand two hundred thirty-four')\n"
        "- Expand acronyms on first occurrence (e.g. 'NATO' → 'NATO, the North Atlantic Treaty Organization')\n"
        "- Convert URLs and emails to a spoken description or omit them\n"
        "- Normalize special characters (e.g. '&' → 'and', '%' → 'percent')\n"
        "- Preserve the original meaning and paragraph structure\n"
        "Return ONLY the optimized text. Do not add commentary or explanation."
    ),
    "light_touch": (
        "You are a proofreading assistant. Make minimal corrections to the following text:\n"
        "- Fix only obvious typos and misspellings\n"
        "- Fix clearly broken punctuation\n"
        "- Do NOT change sentence structure, word choice, or style\n"
        "- Preserve everything else exactly as-is\n"
        "Return ONLY the corrected text. Do not add commentary or explanation."
    ),
}


def get_cleaning_client(
    backend: str,
    api_key: str | None = None,
    custom_base_url: str | None = None,
    custom_api_key: str | None = None,
) -> OpenAI:
    """Return an OpenAI client configured for the chosen cleaning backend."""
    if backend == "custom":
        return OpenAI(
            api_key=custom_api_key or "not-needed",
            base_url=custom_base_url,
        )
    # Default: standard OpenAI
    return OpenAI(api_key=api_key)


def _resolve_model(backend: str, custom_model: str | None) -> str:
    if backend == "custom" and custom_model:
        return custom_model
    return "gpt-4o-mini"


def _resolve_system_prompt(preset: str, custom_prompt: str | None) -> str:
    if preset == "custom" and custom_prompt:
        return custom_prompt
    return PRESET_PROMPTS.get(preset, PRESET_PROMPTS["ocr_cleanup"])


def clean_chunk(
    client: OpenAI,
    model: str,
    system_prompt: str,
    chunk: str,
) -> str:
    """Clean a single text chunk via chat completions."""
    response = client.chat.completions.create(
        model=model,
        temperature=0.3,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": chunk},
        ],
    )
    return response.choices[0].message.content or chunk


def clean_text_chunked(
    client: OpenAI,
    model: str,
    system_prompt: str,
    text: str,
    chunk_size: int = 1500,
    progress_cb: Callable[[float, str], None] | None = None,
) -> str:
    """Split text into chunks, clean each one, and report progress."""
    chunks = split_into_chunks(text, chunk_size=chunk_size)
    if not chunks:
        return text

    cleaned_parts: list[str] = []
    total = len(chunks)

    for i, chunk in enumerate(chunks):
        cleaned = clean_chunk(client, model, system_prompt, chunk)
        cleaned_parts.append(cleaned)
        if progress_cb:
            progress_cb((i + 1) / total, f"Cleaning chunk {i + 1}/{total}")

    return "\n\n".join(cleaned_parts)
