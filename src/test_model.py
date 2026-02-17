#!/usr/bin/env python3
"""Quick test script to verify Qwen3-TTS model loading and voice cloning."""

import torch
import soundfile as sf
from qwen_tts import Qwen3TTSModel
import whisper
from pathlib import Path


def get_device_and_dtype():
    """Auto-detect best device and dtype."""
    if torch.cuda.is_available():
        return "cuda", torch.bfloat16
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps", torch.float32
    else:
        return "cpu", torch.float32


def main():
    device, dtype = get_device_and_dtype()
    print(f"[INFO] Using device: {device}, dtype: {dtype}")

    # Test 1: Whisper transcription
    print("\n[TEST 1] Loading Whisper model...")
    whisper_model = whisper.load_model("base")
    print("[OK] Whisper loaded")

    ref_audio = "sample/sample_amyn_short.wav"
    print(f"[TEST 1] Transcribing {ref_audio}...")
    result = whisper_model.transcribe(ref_audio)
    ref_text = result["text"].strip()
    print(f"[OK] Transcription: {ref_text}")

    # Test 2: Load Qwen3-TTS model
    print("\n[TEST 2] Loading Qwen3-TTS model...")
    print("[INFO] This may take a few minutes on first run (downloading ~6GB)...")
    model = Qwen3TTSModel.from_pretrained(
        "Qwen/Qwen3-TTS-12Hz-1.7B-Base",
        device_map=device,
        torch_dtype=dtype
    )
    print("[OK] Qwen3-TTS model loaded")

    # Test 3: Generate voice clone
    print("\n[TEST 3] Generating voice clone...")
    test_text = "Hello, this is a test of voice cloning on Apple Silicon."

    wavs, sr = model.generate_voice_clone(
        text=test_text,
        language="English",
        ref_audio=ref_audio,
        ref_text=ref_text,
        x_vector_only_mode=False,
        non_streaming_mode=True
    )

    # Save output
    output_dir = Path("audiobooks")
    output_dir.mkdir(exist_ok=True)
    output_path = output_dir / "test_output.wav"
    sf.write(str(output_path), wavs[0], sr)
    print(f"[OK] Saved to {output_path}")
    print(f"[OK] Audio duration: {len(wavs[0]) / sr:.2f} seconds")

    print("\n" + "=" * 50)
    print("ALL TESTS PASSED!")
    print("=" * 50)


if __name__ == "__main__":
    main()
