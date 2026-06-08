"""Transcribe video 2 with small model (faster), then run knowledge step."""
from pathlib import Path

from faster_whisper import WhisperModel

AUDIO = r"D:\batch\audio\BV1Zk9FBwELs_p1.wav"
TEXT_FILE = r"D:\batch\text\BV1Zk9FBwELs_p1.txt"

# Transcribe with small model on CPU
print("Loading whisper small model (CPU)...")
model = WhisperModel("small", device="cpu", compute_type="int8")
print("Starting transcribe...")
segments, info = model.transcribe(AUDIO, beam_size=5)
text = " ".join(seg.text for seg in segments)

with open(TEXT_FILE, "w", encoding="utf-8") as f:
    f.write(text)

print(f"Transcribed: {len(text)} chars, saved to {TEXT_FILE}")
print(f"Detected language: {info.language} (p={info.language_probability:.2f})")
