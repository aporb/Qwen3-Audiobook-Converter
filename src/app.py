"""
VoxCraft — Premium TTS & Audiobook Converter.

Gradio 5.50 UI with dark indigo/purple theme.
Backends: local MLX (Qwen3-TTS on Apple Silicon) or cloud (OpenAI API).

Run: python app.py
"""

import logging
import random
from pathlib import Path

import gradio as gr
import numpy as np

from mlx_tts_engine import (
    MLXTTSEngine, OpenAITTSEngine,
    MLX_SPEAKERS, MLX_LANGUAGES, OPENAI_VOICES, OPENAI_MODELS,
    apply_text_cleaning,
    get_device_info,
    estimate_openai_cost, OPENAI_TTS_PRICING,
    BookMetadata, extract_book_metadata,
    ConversionProgress, OUTPUT_FORMATS,
    extract_text_from_file, split_into_chunks,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

mlx_engine = MLXTTSEngine()
openai_engine = OpenAITTSEngine()


# ---------------------------------------------------------------------------
# CSS (loaded from styles.css next to this file)
# ---------------------------------------------------------------------------

_css_path = Path(__file__).parent / "styles.css"
_css = _css_path.read_text() if _css_path.exists() else ""


# ---------------------------------------------------------------------------
# Theme
# ---------------------------------------------------------------------------

theme = gr.themes.Base(
    primary_hue=gr.themes.colors.indigo,
    secondary_hue=gr.themes.colors.purple,
    neutral_hue=gr.themes.colors.slate,
    font=gr.themes.GoogleFont("Inter"),
).set(
    # Dark backgrounds
    body_background_fill="#0a0a14",
    body_background_fill_dark="#0a0a14",
    background_fill_primary="#111122",
    background_fill_primary_dark="#111122",
    background_fill_secondary="#0d0d1a",
    background_fill_secondary_dark="#0d0d1a",
    # Text colors
    body_text_color="#e8e6f0",
    body_text_color_dark="#e8e6f0",
    body_text_color_subdued="#8b85a8",
    body_text_color_subdued_dark="#8b85a8",
    # Borders
    border_color_primary="rgba(255, 255, 255, 0.06)",
    border_color_primary_dark="rgba(255, 255, 255, 0.06)",
    # Blocks
    block_background_fill="#111122",
    block_background_fill_dark="#111122",
    block_border_color="rgba(255, 255, 255, 0.06)",
    block_border_color_dark="rgba(255, 255, 255, 0.06)",
    block_label_text_color="#8b85a8",
    block_label_text_color_dark="#8b85a8",
    block_title_text_color="#e8e6f0",
    block_title_text_color_dark="#e8e6f0",
    # Inputs
    input_background_fill="rgba(255, 255, 255, 0.03)",
    input_background_fill_dark="rgba(255, 255, 255, 0.03)",
    input_border_color="rgba(255, 255, 255, 0.08)",
    input_border_color_dark="rgba(255, 255, 255, 0.08)",
    input_border_color_focus="#6366f1",
    input_border_color_focus_dark="#6366f1",
    # Buttons
    button_primary_background_fill="linear-gradient(135deg, #4f46e5, #7c3aed)",
    button_primary_background_fill_dark="linear-gradient(135deg, #4f46e5, #7c3aed)",
    button_primary_text_color="white",
    button_primary_text_color_dark="white",
    button_secondary_background_fill="rgba(255, 255, 255, 0.05)",
    button_secondary_background_fill_dark="rgba(255, 255, 255, 0.05)",
    button_secondary_text_color="#e8e6f0",
    button_secondary_text_color_dark="#e8e6f0",
    # Shadows
    shadow_drop="0 4px 12px rgba(0, 0, 0, 0.3)",
    shadow_drop_lg="0 8px 24px rgba(0, 0, 0, 0.4)",
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def get_status_html():
    """Return HTML badges showing current engine status."""
    parts = []
    if mlx_engine.is_loaded:
        model_short = (
            mlx_engine.current_model_id.split("/")[-1]
            if mlx_engine.current_model_id
            else "loaded"
        )
        parts.append(
            f'<span class="badge badge-active">MLX: {model_short}</span>'
        )
    if openai_engine.api_key_available():
        parts.append('<span class="badge badge-info">OpenAI: Connected</span>')
    else:
        parts.append('<span class="badge badge-inactive">OpenAI: No Key</span>')
    if not parts:
        parts.append('<span class="badge badge-inactive">No engine active</span>')
    return (
        '<div id="status-area" style="display:flex; gap:0.5rem; '
        'justify-content:center; flex-wrap:wrap; margin-top:0.75rem;">'
        f'{"".join(parts)}</div>'
    )


def get_device_status_html():
    """Return HTML showing device and memory info."""
    info = get_device_info()
    mem_pct = 0
    if info["memory_total_gb"] > 0:
        mem_pct = int(
            ((info["memory_total_gb"] - info["memory_available_gb"])
             / info["memory_total_gb"]) * 100
        )
    device_chip = f'<span class="device-chip">{info["device"]}</span>'
    if info["accelerator"]:
        device_chip += f' <span class="device-chip">{info["accelerator"]}</span>'
    mem_bar = (
        f'<div class="memory-bar">'
        f'<div class="memory-bar-fill" style="width:{mem_pct}%"></div>'
        f'</div>'
        f'<span class="memory-text">'
        f'{info["memory_available_gb"]}GB / {info["memory_total_gb"]}GB'
        f'</span>'
    )
    return f'<div class="device-status">{device_chip}{mem_bar}</div>'


def get_book_metadata_html(meta):
    """Generate HTML card for book metadata."""
    if meta.cover_image:
        cover = f'<img class="book-cover" src="{meta.cover_image}" alt="Cover">'
    else:
        cover = '<div class="book-cover-placeholder">&#128214;</div>'
    stats = (
        f'<span class="book-stat"><strong>{len(meta.chapters)}</strong> chapters</span>'
        f'<span class="book-stat"><strong>{meta.total_words:,}</strong> words</span>'
        f'<span class="book-stat">{meta.format.upper()}</span>'
    )
    return (
        f'<div class="book-meta-card">'
        f'{cover}'
        f'<div class="book-info">'
        f'<div class="book-title">{meta.title}</div>'
        f'<div class="book-author">{meta.author}</div>'
        f'<div class="book-stats">{stats}</div>'
        f'</div></div>'
    )


def get_cost_estimate_html(text, backend, model):
    """Return cost estimate HTML."""
    if backend == "Offline (MLX)":
        return (
            '<div class="cost-estimate cost-free">'
            '<span class="cost-amount">Free</span>'
            '<span>Local processing -- no API cost</span>'
            '</div>'
        )
    est = estimate_openai_cost(text, model)
    return (
        f'<div class="cost-estimate">'
        f'<span class="cost-amount">${est["estimated_cost_usd"]:.4f}</span>'
        f'<span class="cost-detail">'
        f'{est["characters"]:,} chars '
        f'~{est["estimated_duration_min"]:.0f} min '
        f'{est["model"]}'
        f'</span>'
        f'</div>'
    )


def get_text_highlight_html(text):
    """Generate highlighted text chunks for display."""
    chunks = split_into_chunks(text, chunk_size=50, max_chars=200)
    spans = []
    for i, chunk in enumerate(chunks):
        spans.append(
            f'<span class="chunk" data-chunk="{i}">{chunk}</span> '
        )
    return f'<div class="text-highlight-container">{"".join(spans)}</div>'


def get_waveform_html(num_bars=40):
    """Generate waveform bars HTML."""
    bars = ""
    for _ in range(num_bars):
        h = random.randint(15, 100)
        bars += f'<div class="bar" style="height:{h}%"></div>'
    return (
        f'<div class="waveform-container">'
        f'<div class="waveform-bars">{bars}</div>'
        f'</div>'
    )


VOICE_DESCRIPTIONS = {
    "alloy": "Neutral, balanced",
    "ash": "Warm, conversational",
    "ballad": "Soft, gentle",
    "cedar": "Deep, authoritative",
    "coral": "Bright, expressive",
    "echo": "Calm, measured",
    "fable": "Animated, storytelling",
    "marin": "Clear, professional",
    "nova": "Energetic, youthful",
    "onyx": "Deep, resonant",
    "sage": "Wise, steady",
    "shimmer": "Light, melodic",
    "verse": "Rich, dramatic",
}


def get_voice_cards_html(selected="coral"):
    """Generate voice preview card grid HTML."""
    cards = ""
    for voice, desc in VOICE_DESCRIPTIONS.items():
        sel = " active" if voice == selected else ""
        cards += (
            f'<div class="voice-preview-card{sel}" data-voice="{voice}">'
            f'<div class="voice-name">{voice.title()}</div>'
            f'<div class="voice-desc">{desc}</div>'
            f'</div>'
        )
    return f'<div class="voice-preview-grid">{cards}</div>'


def get_streaming_indicator_html(active=False):
    """Return streaming indicator HTML."""
    if not active:
        return ""
    return (
        '<div class="streaming-indicator">'
        '<span class="pulse-dot"></span>'
        '<span>Generating audio...</span>'
        '</div>'
    )


def update_backend(backend):
    """Toggle visibility of MLX vs OpenAI control groups."""
    is_mlx = backend == "Offline (MLX)"
    return (
        gr.update(visible=is_mlx),       # mlx_controls
        gr.update(visible=not is_mlx),    # openai_controls
        gr.update(visible=not is_mlx),    # voice_gallery
    )


def update_mlx_voice_mode(mode):
    return (
        gr.update(visible=(mode == "Custom Voice")),
        gr.update(visible=(mode == "Voice Clone")),
        gr.update(visible=(mode == "Voice Design")),
    )


def update_openai_instructions_visibility(model):
    """Show instructions field only for gpt-4o-mini-tts."""
    return gr.update(visible=(model == "gpt-4o-mini-tts"))


def do_unload_model():
    """Unload the MLX model and return updated status HTML."""
    try:
        mlx_engine.unload_model()
    except Exception as e:
        raise gr.Error(f"Failed to unload model: {e}")
    return get_status_html()


# ---------------------------------------------------------------------------
# Book upload / metadata callbacks
# ---------------------------------------------------------------------------

def get_resume_status_html(file):
    """Check if a progress file exists for this book."""
    if file is None:
        return ""
    book = Path(file)
    progress_file = Path("audiobooks") / f".{book.stem}_tts.progress.json"
    if not progress_file.exists():
        return ""
    try:
        cp = ConversionProgress.load(progress_file)
        if cp.completed:
            return ""
        pct = int(cp.progress_fraction * 100)
        return (
            f'<div class="conversion-progress">'
            f'<div class="progress-track">'
            f'<div class="progress-fill" style="width:{pct}%"></div>'
            f'</div>'
            f'<span class="resume-badge">Resume available — {cp.completed_chunks}/{cp.total_chunks} chunks done</span>'
            f'</div>'
        )
    except Exception:
        return ""


def on_book_upload(file, backend, oai_model):
    """Handle book file upload -- extract metadata, chapters, cost estimate."""
    if file is None:
        return "", gr.update(choices=[], value=[]), "", ""
    book = Path(file)
    meta = extract_book_metadata(book)
    meta_html = get_book_metadata_html(meta)

    # Build chapter choices
    chapter_choices = [
        f"{ch['title']} ({ch['word_count']:,} words)"
        for ch in meta.chapters
    ]

    # Cost estimate
    try:
        text = extract_text_from_file(book)
        cost_html = get_cost_estimate_html(text, backend, oai_model)
    except Exception:
        cost_html = ""

    resume_status = get_resume_status_html(file)
    return (
        meta_html,
        gr.update(choices=chapter_choices, value=chapter_choices,
                  visible=len(chapter_choices) > 0),
        cost_html,
        resume_status,
    )


def update_cost_on_backend_change(file, backend, oai_model):
    """Update cost estimate when backend changes."""
    if file is None:
        return ""
    book = Path(file)
    try:
        text = extract_text_from_file(book)
        return get_cost_estimate_html(text, backend, oai_model)
    except Exception:
        return ""


# ---------------------------------------------------------------------------
# Generation callbacks
# ---------------------------------------------------------------------------

def generate_tts(
    backend, text,
    # MLX params
    mlx_mode, speaker, cv_lang, instruct,
    ref_audio, ref_text, vc_lang,
    voice_desc, vd_lang,
    # OpenAI params
    oai_voice, oai_model, oai_instructions,
    # Text cleaning
    clean_capitals, clean_footnotes, clean_chars,
    progress=gr.Progress(),
):
    if not text.strip():
        raise gr.Error("Enter some text first.")

    progress(0.02, desc="Cleaning text...")
    cleaned = apply_text_cleaning(text, clean_capitals, clean_footnotes, clean_chars)

    def prog_cb(frac, desc):
        progress(frac, desc=desc)

    try:
        if backend == "Online (OpenAI API)":
            audio, sr = openai_engine.generate_speech(
                text=cleaned, voice=oai_voice, model=oai_model,
                instructions=oai_instructions or None,
                progress_callback=prog_cb,
            )
        else:
            mode = {
                "Custom Voice": "custom_voice",
                "Voice Clone": "voice_clone",
                "Voice Design": "voice_design",
            }[mlx_mode]
            lang = {
                "Custom Voice": cv_lang,
                "Voice Clone": vc_lang,
                "Voice Design": vd_lang,
            }[mlx_mode].lower()
            if mode == "voice_clone" and ref_audio is None:
                raise gr.Error("Upload reference audio for voice cloning.")
            audio, sr = mlx_engine.generate_speech(
                text=cleaned, voice_mode=mode, speaker=speaker, language=lang,
                instruct=instruct if mode == "custom_voice" else None,
                ref_audio=ref_audio if mode == "voice_clone" else None,
                ref_text=ref_text if mode == "voice_clone" else None,
                voice_description=voice_desc if mode == "voice_design" else None,
                progress_callback=prog_cb,
            )

        progress(1.0, desc="Done!")

        return (
            (sr, audio),
            f"Generated {len(audio)/sr:.1f}s of audio",
        )
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(str(e))


def post_generate_updates(text, clean_capitals, clean_footnotes, clean_chars):
    """Update decorative elements after generation completes (no progress overlay)."""
    cleaned = apply_text_cleaning(text, clean_capitals, clean_footnotes, clean_chars)
    return (
        get_status_html(),
        get_text_highlight_html(cleaned),
        get_waveform_html(),
    )


def convert_audiobook(
    backend, file,
    # MLX params
    mlx_mode, speaker, cv_lang, instruct,
    ref_audio, ref_text, vc_lang,
    voice_desc, vd_lang,
    # OpenAI params
    oai_voice, oai_model, oai_instructions,
    # New params
    clean_capitals, clean_footnotes, clean_chars,
    output_format, selected_chapters,
    intro_text, outro_text,
    progress=gr.Progress(),
):
    if file is None:
        raise gr.Error("Upload a book file.")

    import tempfile

    book = Path(file)
    fmt_info = OUTPUT_FORMATS.get(output_format, OUTPUT_FORMATS["wav"])
    out = Path("audiobooks") / f"{book.stem}_tts{fmt_info['ext']}"

    # Extract text, apply cleaning and intro/outro, write to temp file
    raw_text = extract_text_from_file(book)
    cleaned = apply_text_cleaning(raw_text, clean_capitals, clean_footnotes, clean_chars)
    if intro_text and intro_text.strip():
        cleaned = intro_text.strip() + "\n\n" + cleaned
    if outro_text and outro_text.strip():
        cleaned = cleaned + "\n\n" + outro_text.strip()

    tmp = tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8")
    tmp.write(cleaned)
    tmp.close()
    source_path = tmp.name

    try:
        if backend == "Online (OpenAI API)":
            result = openai_engine.generate_audiobook(
                file_path=source_path, output_path=str(out),
                voice=oai_voice, model=oai_model,
                instructions=oai_instructions or None,
                progress_callback=lambda f, d: progress(f, desc=d),
            )
        else:
            mode = {
                "Custom Voice": "custom_voice",
                "Voice Clone": "voice_clone",
                "Voice Design": "voice_design",
            }[mlx_mode]
            lang = {
                "Custom Voice": cv_lang,
                "Voice Clone": vc_lang,
                "Voice Design": vd_lang,
            }[mlx_mode].lower()
            if mode == "voice_clone" and ref_audio is None:
                raise gr.Error("Upload reference audio for voice cloning.")
            result = mlx_engine.generate_audiobook(
                file_path=source_path, voice_mode=mode, output_path=str(out),
                speaker=speaker, language=lang,
                instruct=instruct if mode == "custom_voice" else None,
                ref_audio=ref_audio if mode == "voice_clone" else None,
                ref_text=ref_text if mode == "voice_clone" else None,
                voice_description=voice_desc if mode == "voice_design" else None,
                progress_callback=lambda f, d: progress(f, desc=d),
            )

        return result, f"Saved: {result}", get_status_html()
    except gr.Error:
        raise
    except Exception as e:
        raise gr.Error(str(e))
    finally:
        import os as _os
        _os.unlink(source_path)


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

def build_ui():
    mlx_langs = [lang.capitalize() for lang in MLX_LANGUAGES]
    is_openai_default = openai_engine.api_key_available()

    with gr.Blocks(css=_css, theme=theme, title="VoxCraft") as app:

        # ---- Header ----
        gr.HTML(
            '<div id="voxcraft-header">'
            "<h1>VoxCraft</h1>"
            "<p>Transform text into natural speech "
            "-- Local MLX on Apple Silicon or OpenAI Cloud</p>"
            "</div>"
        )
        status_html = gr.HTML(value=get_status_html())
        device_html = gr.HTML(value=get_device_status_html())

        # ---- Sidebar (Settings) ----
        with gr.Sidebar(
            label="Settings", open=False, width=340,
            elem_classes=["settings-sidebar"],
        ):
            backend = gr.Radio(
                ["Offline (MLX)", "Online (OpenAI API)"],
                value="Online (OpenAI API)" if is_openai_default else "Offline (MLX)",
                label="Backend",
            )

            # -- MLX Voice Settings --
            with gr.Accordion(
                "MLX Voice Settings", open=True,
                visible=not is_openai_default,
            ) as mlx_controls:
                mlx_mode = gr.Radio(
                    ["Custom Voice", "Voice Clone", "Voice Design"],
                    value="Custom Voice",
                    label="Voice Mode",
                )

                # Custom Voice options
                with gr.Group(visible=True) as cv_group:
                    speaker = gr.Dropdown(
                        MLX_SPEAKERS, value="Ryan", label="Speaker",
                    )
                    cv_lang = gr.Dropdown(
                        mlx_langs, value="English", label="Language",
                    )
                    instruct = gr.Textbox(
                        label="Style Instruction",
                        value="Read in a clear, professional narrator's voice.",
                        lines=2,
                    )

                # Voice Clone options
                with gr.Group(visible=False) as vc_group:
                    ref_audio = gr.Audio(
                        label="Reference Audio",
                        type="filepath",
                        sources=["upload"],
                    )
                    vc_lang = gr.Dropdown(
                        mlx_langs, value="English", label="Language",
                    )
                    ref_text = gr.Textbox(
                        label="Reference Text (optional)", lines=2,
                    )

                # Voice Design options
                with gr.Group(visible=False) as vd_group:
                    vd_lang = gr.Dropdown(
                        mlx_langs, value="English", label="Language",
                    )
                    voice_desc = gr.Textbox(
                        label="Voice Description",
                        placeholder="A deep, warm male voice with a British accent.",
                        lines=3,
                    )

                mlx_mode.change(
                    update_mlx_voice_mode, mlx_mode,
                    [cv_group, vc_group, vd_group],
                )

            # -- OpenAI Settings --
            with gr.Accordion(
                "OpenAI Settings", open=True,
                visible=is_openai_default,
            ) as openai_controls:
                oai_voice = gr.Dropdown(
                    OPENAI_VOICES, value="coral", label="Voice",
                )
                oai_model = gr.Dropdown(
                    OPENAI_MODELS, value="gpt-4o-mini-tts", label="Model",
                )
                oai_instructions = gr.Textbox(
                    label="Instructions (tone, accent, style -- gpt-4o-mini-tts only)",
                    placeholder="Speak in a warm, friendly tone with a slight British accent.",
                    lines=2,
                    visible=True,
                )
                oai_model.change(
                    update_openai_instructions_visibility,
                    oai_model,
                    oai_instructions,
                )

            # -- Voice Gallery (visual only) --
            with gr.Accordion("Voice Gallery", open=False, visible=is_openai_default) as voice_gallery:
                voice_cards_html = gr.HTML(value=get_voice_cards_html())

            # Backend toggle wiring
            backend.change(
                update_backend, backend, [mlx_controls, openai_controls, voice_gallery],
            )

            oai_voice.change(
                get_voice_cards_html, oai_voice, voice_cards_html,
            )

            # -- Text Processing --
            with gr.Accordion("Text Processing", open=False):
                with gr.Column(elem_classes=["text-cleaning-panel"]):
                    clean_capitals = gr.Checkbox(
                        label="Fix spaced capitals", value=True,
                    )
                    clean_footnotes = gr.Checkbox(
                        label="Remove footnote markers", value=True,
                    )
                    clean_chars = gr.Checkbox(
                        label="Normalize special characters", value=True,
                    )

            # -- Output Format --
            with gr.Accordion("Output Format", open=False):
                output_format = gr.Radio(
                    choices=list(OUTPUT_FORMATS.keys()),
                    value="wav",
                    label="Audio Format",
                    info="WAV is lossless; M4B supports chapters; MP3 is most compatible.",
                )

            # -- Intro / Outro Announcements --
            with gr.Accordion("Intro / Outro", open=False):
                with gr.Column(elem_classes=["announcement-fields"]):
                    intro_text = gr.Textbox(
                        label="Intro Announcement",
                        placeholder="This audiobook was generated by VoxCraft...",
                        lines=2,
                    )
                    outro_text = gr.Textbox(
                        label="Outro Announcement",
                        placeholder="End of audiobook. Thank you for listening.",
                        lines=2,
                    )

            # Unload button
            unload_btn = gr.Button(
                "Unload MLX Model", size="sm", variant="secondary",
            )
            unload_btn.click(
                fn=do_unload_model,
                outputs=status_html,
            )

        # ---- Input lists ----
        mlx_inputs = [
            mlx_mode, speaker, cv_lang, instruct,
            ref_audio, ref_text, vc_lang,
            voice_desc, vd_lang,
        ]
        oai_inputs = [oai_voice, oai_model, oai_instructions]
        cleaning_inputs = [clean_capitals, clean_footnotes, clean_chars]

        # ---- Tabs ----
        with gr.Tabs(elem_classes=["page-nav"]):

            # -- Quick TTS --
            with gr.TabItem("Quick TTS"):
                with gr.Column(elem_classes=["glass-panel"]):
                    gr.Markdown("### Text to Speech")
                    text_in = gr.Textbox(
                        label="Text",
                        placeholder="Enter or paste text...",
                        lines=8,
                        elem_classes=["main-input"],
                    )
                    gen_btn = gr.Button(
                        "Generate Speech",
                        variant="primary",
                        size="lg",
                        elem_classes=["action-btn"],
                    )
                    streaming_indicator = gr.HTML(value="")
                    audio_out = gr.Audio(
                        label="Generated Audio", type="numpy",
                    )
                    waveform_display = gr.HTML(
                        value=get_waveform_html(), visible=True,
                    )
                    tts_status = gr.Textbox(
                        label="Status", interactive=False,
                    )
                    text_highlight = gr.HTML(value="")

                    with gr.Column(elem_classes=["example-area"]):
                        gr.Examples(
                            examples=[
                                "The old house on the hill had stood there for generations, "
                                "its weathered walls telling stories of families who had "
                                "called it home.",
                                "Welcome to today's episode. We're going to explore the "
                                "fascinating world of deep-sea creatures and their "
                                "incredible adaptations.",
                                "It was a truth universally acknowledged, that a single "
                                "man in possession of a good fortune, must be in want "
                                "of a wife.",
                            ],
                            inputs=text_in,
                            label="Try an example",
                        )

                    gen_btn.click(
                        generate_tts,
                        [backend, text_in, *mlx_inputs, *oai_inputs, *cleaning_inputs],
                        [audio_out, tts_status],
                    ).then(
                        post_generate_updates,
                        [text_in, *cleaning_inputs],
                        [status_html, text_highlight, waveform_display],
                    )

            # -- Audiobook Converter --
            with gr.TabItem("Audiobook Converter"):
                with gr.Column(elem_classes=["glass-panel"]):
                    gr.Markdown("### Convert Books to Audio")
                    file_in = gr.File(
                        label="Upload Book",
                        file_types=[".epub", ".pdf", ".txt", ".docx", ".doc"],
                        type="filepath",
                    )

                    # Metadata display (populated on upload)
                    book_meta_html = gr.HTML(value="")
                    cost_html = gr.HTML(value="")
                    resume_html = gr.HTML(value="")

                    # Chapter selection
                    chapter_select = gr.CheckboxGroup(
                        choices=[], value=[], label="Chapters to Convert",
                        visible=False,
                    )

                    # Wire file upload
                    file_in.change(
                        on_book_upload,
                        [file_in, backend, oai_model],
                        [book_meta_html, chapter_select, cost_html, resume_html],
                    )

                    # Update cost when backend changes
                    backend.change(
                        update_cost_on_backend_change,
                        [file_in, backend, oai_model],
                        cost_html,
                    )

                    book_streaming = gr.HTML(value="")
                    conv_btn = gr.Button(
                        "Convert to Audiobook",
                        variant="primary",
                        size="lg",
                        elem_classes=["action-btn"],
                    )
                    book_out = gr.File(label="Download Audiobook")
                    book_status = gr.Textbox(
                        label="Status", interactive=False,
                    )

                    conv_btn.click(
                        convert_audiobook,
                        [backend, file_in, *mlx_inputs, *oai_inputs,
                         *cleaning_inputs, output_format, chapter_select,
                         intro_text, outro_text],
                        [book_out, book_status, status_html],
                    )

    return app


if __name__ == "__main__":
    build_ui().launch(server_name="127.0.0.1", server_port=7860)
