"""Use existing OpenVINO model to transcribe video 2."""
import sys
import os

# This import triggers OpenVINO runtime loading - may take a minute
print("Loading optimum.intel (this may take a while)...")
sys.stdout.flush()
from optimum.intel import OVModelForSpeechSeq2Seq
from transformers import WhisperProcessor

AUDIO = r"D:\batch\audio\BV1Zk9FBwELs_p1.wav"
TEXT_FILE = r"D:\batch\text\BV1Zk9FBwELs_p1.txt"
MODEL_DIR = r"D:\batch\whisper-model\medium"

print("Loading model...")
sys.stdout.flush()
processor = WhisperProcessor.from_pretrained("openai/whisper-medium")
model = OVModelForSpeechSeq2Seq.from_pretrained(
    MODEL_DIR,
    export=False,
    compile=True,
    device="CPU",  # CPU even for OV - avoids GPU driver issues
    ov_config={"PERFORMANCE_HINT": "LATENCY"},
)

print("Loading audio...")
sys.stdout.flush()
import soundfile as sf
import numpy as np

audio, sr = sf.read(AUDIO, dtype="float32")
if audio.ndim > 1:
    audio = audio.mean(axis=1)
if sr != 16000:
    import librosa
    audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

duration = len(audio) / 16000.0
print(f"Audio: {len(audio)} samples, {duration:.0f}s, sr={sr}")
sys.stdout.flush()

# Chunked transcription (30s windows)
CHUNK_SAMPLES = 30 * 16000
total = len(audio)
texts = []
sot = processor.tokenizer.convert_tokens_to_ids("<|startoftranscript|>")
zh = processor.tokenizer.convert_tokens_to_ids("<|zh|>")
trans = processor.tokenizer.convert_tokens_to_ids("<|transcribe|>")
nots = processor.tokenizer.convert_tokens_to_ids("<|notimestamps|>")
eos = processor.tokenizer.eos_token_id

offset = 0
chunk_no = 0
while offset < total:
    chunk = audio[offset:offset+CHUNK_SAMPLES]
    feats = processor.feature_extractor(chunk, sampling_rate=16000, return_tensors="np").input_features
    enc = model.encoder(input_features=feats)
    hs = enc.last_hidden_state
    tokens = [sot, zh, trans, nots]
    for _ in range(448):
        decoder_input = np.array([tokens], dtype=np.int64)
        dout = model.decoder(input_ids=decoder_input, encoder_hidden_states=hs)
        next_tok = int(np.argmax(dout.logits[0, -1]))
        if next_tok == eos:
            break
        tokens.append(next_tok)
    text = processor.tokenizer.decode(tokens, skip_special_tokens=True)
    if text.strip():
        texts.append(text.strip())
    chunk_no += 1
    offset += CHUNK_SAMPLES
    print(f"  Chunk {chunk_no}: {len(text)} chars")
    sys.stdout.flush()

full_text = "\n".join(texts)
with open(TEXT_FILE, "w", encoding="utf-8") as f:
    f.write(full_text)

print(f"DONE: {len(full_text)} chars, saved to {TEXT_FILE}")
