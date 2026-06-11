from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.task import Task

# Python 3.14 兼容：functools.partial.__get__ 破坏了 optimum 的类属性访问
# 必须在任何 optimum import 之前应用此补丁
for _p in sys.path:
    if not _p:
        continue
    for _rel in ("optimum/exporters/base.py", "optimum/exporters/openvino/model_configs.py"):
        _fp = Path(_p) / _rel
        if _fp.exists():
            _content = _fp.read_text(encoding="utf-8")
            _old = "self.NORMALIZED_CONFIG_CLASS(self._config)"
            _new = "type(self).NORMALIZED_CONFIG_CLASS(self._config)"
            if _old in _content:
                _fp.write_text(_content.replace(_old, _new), encoding="utf-8")

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
    """使用 OpenVINO + optimum-intel 在 Intel GPU 上运行 Whisper。

    通过 model.generate() 进行推理，利用 KV 缓存加速自回归解码。
    首次运行时自动导出 OpenVINO IR 模型并缓存到本地。
    """

    # 30 秒窗口 = 480,000 采样点 @ 16kHz
    _CHUNK_SAMPLES = 30 * 16000

    def __init__(self, model_size: str, model_dir: str) -> None:
        from optimum.intel import OVModelForSpeechSeq2Seq
        from transformers import WhisperProcessor

        model_id = f"openai/whisper-{model_size}"
        local_path = Path(model_dir) / model_size

        # 始终从 HuggingFace 加载 processor（tokenizer + feature extractor，体积小）
        self._processor = WhisperProcessor.from_pretrained(model_id)
        self._model_id = model_id

        # 检查本地是否已有导出过的 OpenVINO IR 模型
        if (local_path / "openvino_encoder_model.xml").exists():
            logger.info("从本地缓存加载 OpenVINO IR 模型: {}", local_path)
            self._model = OVModelForSpeechSeq2Seq.from_pretrained(
                str(local_path),
                export=False,
                compile=True,
                device="GPU",
                ov_config={"PERFORMANCE_HINT": "LATENCY"},
            )
        else:
            logger.info("首次加载，导出 OpenVINO IR 模型: {} → {}", model_id, local_path)
            self._model = OVModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                export=True,
                compile=True,
                device="GPU",
                ov_config={"PERFORMANCE_HINT": "LATENCY"},
            )
            local_path.mkdir(parents=True, exist_ok=True)
            self._model.save_pretrained(str(local_path))
            logger.info("OpenVINO IR 模型已缓存到: {}", local_path)

        logger.info("OVWhisperModel 加载成功: model={}, device=GPU", model_id)

    def transcribe(self, audio_path: str) -> tuple[str, float]:
        audio = self._load_audio(audio_path)
        duration = len(audio) / 16000.0

        total_samples = len(audio)
        if total_samples <= self._CHUNK_SAMPLES:
            text = self._transcribe_chunk(audio)
            return text, duration

        # 长音频：按 30 秒窗口分片，逐段推理
        texts: list[str] = []
        offset = 0
        chunk_idx = 0
        while offset < total_samples:
            chunk = audio[offset : offset + self._CHUNK_SAMPLES]
            chunk_text = self._transcribe_chunk(chunk)
            if chunk_text:
                texts.append(chunk_text)
            chunk_idx += 1
            offset += self._CHUNK_SAMPLES

        logger.info("分片转写完成: {} 段, {} 段非空", chunk_idx, len(texts))
        return "\n".join(texts), duration

    def _transcribe_chunk(self, audio_chunk) -> str:
        """对单个音频片段使用 model.generate() 执行推理。

        相比较手动逐 token 调用 encoder/decoder:
        - generate() 内置 KV 缓存，避免重复计算历史 token 的 attention
        - 时间复杂度从 O(n²) 降到 O(n)
        """
        import numpy as np
        import torch

        input_features = self._processor.feature_extractor(
            audio_chunk, sampling_rate=16000, return_tensors="pt",
        ).input_features

        # model.generate() 需要 input_features 作为 inputs
        generated = self._model.generate(
            input_features,
            language="zh",
            task="transcribe",
            return_timestamps=False,
            max_new_tokens=444,
        )

        # generated 可能是 torch.Tensor 或 numpy array
        if isinstance(generated, torch.Tensor):
            generated = generated.cpu().numpy()
        elif not isinstance(generated, np.ndarray):
            generated = np.array(generated)

        return self._processor.tokenizer.decode(
            generated[0], skip_special_tokens=True,
        )

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
