"""Intel GPU Whisper 推理测试脚本。

验证流程：
  1. 检测 OpenVINO GPU 可用性
  2. 应用 optimum Python 3.14 兼容补丁
  3. 导出/加载 Whisper 模型 → OpenVINO IR
  4. GPU 推理 + 性能报告

用法:
  uv run python scripts/test_gpu_whisper.py                    # 用 tiny 模型快速测试
  uv run python scripts/test_gpu_whisper.py --model medium     # 用 medium 模型
  uv run python scripts/test_gpu_whisper.py --audio <path>     # 指定测试音频

首次运行会自动从 HF 镜像下载并导出 OpenVINO IR 模型（tiny ~1min, medium ~5-15min）。
后续运行直接从缓存加载（~5s）。
"""

from __future__ import annotations

# ── 必须在所有 HF 相关 import 之前设置镜像 + 并发下载 ──
import os as _os
if not _os.environ.get("HF_ENDPOINT"):
    _os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
# hf_transfer: Rust 并发分块下载, 4 路并发
_os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"
_os.environ["HF_TRANSFER_CONCURRENCY"] = "4"

import argparse
import sys
import time
import warnings
from pathlib import Path

# 抑制 transformers 的配置迁移警告（不影响功能）
warnings.filterwarnings("ignore", message=".*Moving the following attributes.*")
warnings.filterwarnings("ignore", message=".*`loss_type=None` was set.*")
warnings.filterwarnings("ignore", message=".*attention mask is not set.*")

# ---------------------------------------------------------------------------
# Python 3.14 兼容补丁
# ---------------------------------------------------------------------------


def _patch_optimum_py314() -> int:
    """修复 optimum 在 Python 3.14 上的 functools.partial 描述符问题。"""
    patched = 0
    for p in sys.path:
        if not p:
            continue
        root = Path(p)
        for rel in [
            "optimum/exporters/base.py",
            "optimum/exporters/openvino/model_configs.py",
        ]:
            fp = root / rel
            if not fp.exists():
                continue
            content = fp.read_text(encoding="utf-8")
            old = "self.NORMALIZED_CONFIG_CLASS(self._config)"
            new = "type(self).NORMALIZED_CONFIG_CLASS(self._config)"
            count = content.count(old)
            if count:
                content = content.replace(old, new)
                fp.write_text(content, encoding="utf-8")
                patched += count
    return patched


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

MODEL_DIR = Path("/home/xu/workspace/batch/whisper-model")
DEFAULT_AUDIO = "/home/xu/workspace/batch/audio/7649439389990398180.wav"


def check_gpu() -> None:
    """检查 OpenVINO GPU 可用性。"""
    from openvino import Core

    core = Core()
    devices = core.available_devices
    print(f"[GPU 检测] 可用设备: {devices}")
    if "GPU" not in devices:
        print("警告: GPU 不可用，将降级到 CPU！")
    else:
        name = core.get_property("GPU", "FULL_DEVICE_NAME")
        print(f"  GPU: {name}")


def load_model(model_size: str, device: str) -> tuple:
    """加载或导出模型，返回 (model, processor)。"""
    from optimum.intel import OVModelForSpeechSeq2Seq
    from transformers import WhisperProcessor

    model_id = f"openai/whisper-{model_size}"
    local_path = MODEL_DIR / model_size

    print(f"\n[模型加载] size={model_size}, device={device}")

    # Processor（始终从 HF 下载，体积小）
    print("  加载 processor...")
    t0 = time.time()
    processor = WhisperProcessor.from_pretrained(model_id)
    print(f"  processor 就绪 ({time.time() - t0:.1f}s)")

    # Model: 从缓存加载或首次导出
    if (local_path / "openvino_encoder_model.xml").exists():
        print(f"  从缓存加载 IR 模型: {local_path}")
        t0 = time.time()
        model = OVModelForSpeechSeq2Seq.from_pretrained(
            str(local_path),
            export=False,
            compile=True,
            device=device,
            ov_config={"PERFORMANCE_HINT": "LATENCY"},
        )
        print(f"  模型加载完成 ({time.time() - t0:.1f}s)")
    else:
        print(f"  首次运行: 导出 {model_id} → {local_path}")
        print(f"  (tiny ~1min, medium ~5-15min, 请耐心等待)")
        t0 = time.time()
        model = OVModelForSpeechSeq2Seq.from_pretrained(
            model_id,
            export=True,
            compile=True,
            device=device,
            ov_config={"PERFORMANCE_HINT": "LATENCY"},
        )
        elapsed = time.time() - t0
        print(f"  导出+编译完成 ({elapsed:.0f}s / {elapsed / 60:.1f}min)")
        local_path.mkdir(parents=True, exist_ok=True)
        model.save_pretrained(str(local_path))
        print(f"  已缓存到: {local_path}")

    # 打印模型文件大小
    total_mb = sum(f.stat().st_size for f in local_path.rglob("*") if f.is_file()) / (1024 * 1024)
    print(f"  模型文件总大小: {total_mb:.0f} MB")

    return model, processor


def transcribe_audio(
    model, processor, audio_path: str, max_duration: float = 30.0
) -> tuple[str, float, float]:
    """转写音频文件，返回 (文本, 音频时长秒, 推理耗时秒)。"""
    import numpy as np
    import soundfile as sf
    import torch

    # 加载音频
    audio, sr = sf.read(audio_path, dtype="float32")
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != 16000:
        import librosa
        audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)

    max_samples = int(max_duration * 16000)
    audio = audio[:max_samples]
    audio_duration = len(audio) / 16000.0
    print(f"  音频: {audio_duration:.1f}s, {len(audio)} samples")

    # 特征提取
    input_features = processor.feature_extractor(
        audio, sampling_rate=16000, return_tensors="pt",
    ).input_features

    # GPU 推理
    print("  推理中...")
    t0 = time.time()
    generated = model.generate(
        input_features,
        language="zh",
        task="transcribe",
        return_timestamps=False,
        max_new_tokens=444,
    )
    if isinstance(generated, torch.Tensor):
        generated = generated.cpu().numpy()
    elapsed = time.time() - t0

    text = processor.tokenizer.decode(generated[0], skip_special_tokens=True)
    return text, audio_duration, elapsed


def main() -> None:
    parser = argparse.ArgumentParser(description="Intel GPU Whisper 推理测试")
    parser.add_argument(
        "--model", default="tiny",
        choices=["tiny", "small", "medium"],
        help="Whisper 模型大小 (默认: tiny)",
    )
    parser.add_argument(
        "--audio", default=DEFAULT_AUDIO,
        help=f"测试音频路径 (默认: {DEFAULT_AUDIO})",
    )
    parser.add_argument(
        "--max-duration", type=float, default=30.0,
        help="最大推理音频时长(秒) (默认: 30)",
    )
    parser.add_argument(
        "--device", default="GPU",
        choices=["GPU", "CPU"],
        help="推理设备 (默认: GPU)",
    )
    args = parser.parse_args()

    # 检查音频文件
    if not Path(args.audio).exists():
        print(f"错误: 音频文件不存在: {args.audio}")
        print("请用 --audio 指定存在的音频文件")
        sys.exit(1)

    print("=" * 60)
    print("  Intel GPU Whisper 推理测试")
    print(f"  模型: {args.model}")
    print(f"  设备: {args.device}")
    print(f"  音频: {args.audio}")
    print("=" * 60)

    # Step 1: 检查 GPU
    check_gpu()

    # Step 2: Python 3.14 补丁
    n = _patch_optimum_py314()
    if n:
        print(f"\n[补丁] 已修复 optimum Python 3.14 兼容性 ({n} 处)")

    # Step 3: 加载模型
    model, processor = load_model(args.model, args.device)

    # Step 4: 推理测试
    print(f"\n[推理测试] {args.audio}")
    text, duration, elapsed = transcribe_audio(
        model, processor, args.audio, args.max_duration,
    )

    # Step 5: 结果报告
    print("\n" + "=" * 60)
    print("  推理结果")
    print("=" * 60)
    print(f"  音频时长:    {duration:.1f}s")
    print(f"  推理耗时:    {elapsed:.1f}s")
    print(f"  实时率:      {duration / elapsed:.1f}x")
    print(f"  转写文本:")
    print(f"  {text[:500]}{'...' if len(text) > 500 else ''}")
    print("=" * 60)

    if duration / elapsed >= 1:
        print(f"\n✓ GPU 加速可用 ({duration / elapsed:.1f}x 实时)")
    else:
        print(f"\n⚠ 推理速度低于实时 ({duration / elapsed:.1f}x)，检查 GPU 是否正常")


if __name__ == "__main__":
    main()
