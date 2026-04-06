from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.task import Task
from hot_pulse.worker_base import run_worker

_model: TranscribeModel | None = None


# ---------------------------------------------------------------------------
# TranscribeModel protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class TranscribeModel(Protocol):
    """转写模型协议。"""

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        """转写音频文件，返回 (文本, 音频时长秒)。"""
        ...


# ---------------------------------------------------------------------------
# GPU path: OpenVINO + optimum-intel
# ---------------------------------------------------------------------------

class OVWhisperModel:
    """使用 OpenVINO + optimum-intel 在 Intel GPU 上运行 Whisper。"""

    def __init__(self, model_size: str, model_dir: str) -> None:
        from optimum.intel import OVModelForSpeechSeq2Seq
        from transformers import WhisperProcessor

        model_id = f"openai/whisper-{model_size}"
        local_path = Path(model_dir) / model_size

        # 始终从 HuggingFace 加载 processor（体积小，无需缓存）
        self._processor = WhisperProcessor.from_pretrained(model_id)

        # 检查本地是否已有导出过的 OpenVINO 模型
        if (local_path / "openvino_encoder_model.xml").exists():
            logger.info("从本地缓存加载 OpenVINO 模型: {}", local_path)
            self._model = OVModelForSpeechSeq2Seq.from_pretrained(
                str(local_path),
                export=False,
                compile=True,
                device="GPU",
                ov_config={"PERFORMANCE_HINT": "CUMULATIVE_THROUGHPUT"},
            )
        else:
            logger.info("首次加载，导出 OpenVINO 模型: {} → {}", model_id, local_path)
            self._model = OVModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                export=True,
                compile=True,
                device="GPU",
                ov_config={"PERFORMANCE_HINT": "CUMULATIVE_THROUGHPUT"},
            )
            local_path.mkdir(parents=True, exist_ok=True)
            self._model.save_pretrained(str(local_path))
            logger.info("OpenVINO 模型已缓存到: {}", local_path)

        # Pre-cache special token IDs
        tok = self._processor.tokenizer
        self._sot = tok.convert_tokens_to_ids("<|startoftranscript|>")
        self._zh = tok.convert_tokens_to_ids("<|zh|>")
        self._transcribe_tok = tok.convert_tokens_to_ids("<|transcribe|>")
        self._notimestamps = tok.convert_tokens_to_ids("<|notimestamps|>")
        self._eos = tok.eos_token_id

        logger.info("OVWhisperModel 加载成功: model={}, device=GPU", model_id)

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        import numpy as np

        # 加载音频 (extract_audio_worker 已输出 16kHz mono WAV)
        audio = self._load_audio(audio_path)
        duration = len(audio) / 16000.0

        # 提取 mel features (numpy)
        input_features = self._processor.feature_extractor(
            audio, sampling_rate=16000, return_tensors="np",
        ).input_features

        # Encoder 前向推理
        encoder_out = self._model.encoder(input_features=input_features)
        hidden_states = encoder_out.last_hidden_state

        # Decoder greedy decode 循环
        max_tokens = 448
        tokens = [self._sot, self._zh, self._transcribe_tok, self._notimestamps]

        for _ in range(max_tokens):
            decoder_input = np.array([tokens], dtype=np.int64)
            decoder_out = self._model.decoder(
                input_ids=decoder_input,
                encoder_hidden_states=hidden_states,
            )
            next_token = int(np.argmax(decoder_out.logits[0, -1]))
            if next_token == self._eos:
                break
            tokens.append(next_token)

        text = self._processor.tokenizer.decode(tokens, skip_special_tokens=True)
        return text, duration

    @staticmethod
    def _load_audio(path: str):
        """读取 16kHz mono WAV 返回 float32 numpy 数组。"""
        import numpy as np
        import soundfile as sf

        audio, sr = sf.read(path, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if sr != 16000:
            import librosa
            audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
        return audio


# ---------------------------------------------------------------------------
# CPU path: faster-whisper (original)
# ---------------------------------------------------------------------------

class FasterWhisperModel:
    """使用 faster-whisper 在 CPU 上运行 Whisper。"""

    def __init__(self, model_size: str) -> None:
        from faster_whisper import WhisperModel

        self._model = WhisperModel(model_size, device="cpu", compute_type="int8")
        logger.info("FasterWhisperModel 加载成功: model={}, device=cpu", model_size)

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        segments, info = self._model.transcribe(audio_path, language="zh")
        text_lines = [seg.text.strip() for seg in segments if seg.text.strip()]
        text = "\n".join(text_lines)
        return text, info.duration


# ---------------------------------------------------------------------------
# Model initialization & singleton
# ---------------------------------------------------------------------------

def _init_model(config: AppConfig) -> TranscribeModel:
    """根据配置初始化转写模型，GPU 不可用时降级 CPU。"""
    model_size = config.transcribe_worker.model_size
    model_dir = config.transcribe_worker.model_dir
    device = config.transcribe_worker.device

    # 国内网络默认使用 HuggingFace 镜像加速模型下载
    if not os.environ.get("HF_ENDPOINT"):
        os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

    if device == "gpu":
        try:
            return OVWhisperModel(model_size, model_dir)
        except Exception as e:
            logger.warning("GPU 模型加载失败 ({}), 降级到 CPU", e)

    return FasterWhisperModel(model_size)


def _get_model(config: AppConfig) -> TranscribeModel:
    """获取缓存的模型实例，首次调用时初始化。"""
    global _model
    if _model is None:
        _model = _init_model(config)
    return _model


# ---------------------------------------------------------------------------
# Transcribe logic
# ---------------------------------------------------------------------------

def _transcribe(audio_file: str, text_dir: str, video_id: str, config: AppConfig) -> str:
    """使用转写模型将音频转为纯文本，GPU 推理失败时单次降级 CPU。"""
    model = _get_model(config)

    dir_path = Path(text_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    logger.info("开始转写: video_id={}, audio_file={}", video_id, audio_file)

    try:
        text, duration = model.transcribe(audio_file)
    except Exception as e:
        if isinstance(model, OVWhisperModel):
            logger.warning("GPU 转写失败 ({}), 降级到 CPU", e)
            global _model
            _model = FasterWhisperModel(config.transcribe_worker.model_size)
            text, duration = _model.transcribe(audio_file)
        else:
            raise

    text_file = dir_path / f"{video_id}.txt"
    text_file.write_text(text, encoding="utf-8")

    logger.info(
        "转写完成: video_id={}, chars={}, duration={:.1f}s",
        video_id, len(text), duration,
    )
    return str(text_file)


def handle_transcribe(task: Task, config: AppConfig) -> dict[str, Any]:
    """Transcribe worker 的业务 handler。"""
    audio_file = task.inputs.get("audio_file")
    if not audio_file:
        raise RuntimeError("Task inputs 中无 audio_file")

    path = Path(audio_file)
    if not path.exists():
        raise RuntimeError(f"音频文件不存在: {audio_file}")

    text_file = _transcribe(
        audio_file, config.transcribe_worker.text_dir, task.video_id, config,
    )
    return {"text_file": text_file}


def run_transcribe_worker(config_path: str = "config.yaml") -> None:
    """启动 transcribe worker。"""
    run_worker("transcribe", handle_transcribe, config_path)


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")

    run_transcribe_worker()
