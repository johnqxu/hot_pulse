from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.task import Task


def _extract_audio(video_file: str, audio_dir: str, video_id: str) -> str:
    """使用 ffmpeg 从视频文件中提取音频为 16kHz 单声道 WAV 格式。

    Args:
        video_file: 视频文件路径
        audio_dir: 音频输出目录
        video_id: 视频 ID，用于命名输出文件

    Returns:
        音频文件路径
    """
    dir_path = Path(audio_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    audio_file = dir_path / f"{video_id}.wav"

    cmd = [
        "ffmpeg", "-i", video_file,
        "-vn",           # 不包含视频
        "-ar", "16000",  # 16kHz 采样率
        "-ac", "1",      # 单声道
        str(audio_file),
        "-y",             # 覆盖已存在的文件
    ]

    logger.info("提取音频: video_id={}, video_file={}", video_id, video_file)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except FileNotFoundError:
        raise RuntimeError("ffmpeg 未安装，请先安装 ffmpeg 并确保在 PATH 中")
    except subprocess.CalledProcessError as e:
        # 取 stderr 末尾（ffmpeg 真正的错误信息在最后）
        err = e.stderr.strip()
        raise RuntimeError(f"ffmpeg 提取音频失败: {err[-500:] if len(err) > 500 else err}")

    size_mb = audio_file.stat().st_size / (1024 * 1024)
    logger.info("音频提取完成: video_id={}, size={:.1f}MB", video_id, size_mb)
    return str(audio_file)


def handle_extract_audio(task: Task, config: AppConfig) -> dict[str, Any]:
    """Extract audio worker 的业务 handler。"""
    video_file = task.inputs.get("video_file")
    if not video_file:
        raise RuntimeError("Task inputs 中无 video_file")

    audio_file = _extract_audio(
        video_file, config.extract_audio_worker.audio_dir, task.video_id,
    )
    return {"audio_file": audio_file}
