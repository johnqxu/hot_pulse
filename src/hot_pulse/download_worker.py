from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx
from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.task import Task
from hot_pulse.worker_base import run_worker


def _get_url_priority(url: str, url_priority: dict[str, int]) -> int:
    """根据域名匹配 url_priority 配置返回优先级。

    匹配规则：
    - 精确匹配（如 "v26-web.douyinvod.com"）优先
    - 通配符匹配（如 "*.douyinvod.com"）匹配任意子域
    - 未匹配返回 0
    """
    hostname = urlparse(url).hostname or ""
    best_priority = 0

    for pattern, priority in url_priority.items():
        if pattern.startswith("*."):
            # 通配符匹配：*.example.com 匹配 sub.example.com
            suffix = pattern[1:]  # .example.com
            if hostname.endswith(suffix) or hostname == pattern[2:]:
                best_priority = max(best_priority, priority)
        elif hostname == pattern:
            # 精确匹配优先级最高，直接返回
            return priority
        best_priority = max(best_priority, 0)

    return best_priority


def _sort_urls_by_priority(urls: list[str], url_priority: dict[str, int]) -> list[str]:
    """按 url_priority 对 URL 列表排序，优先级高的在前，同优先级保持原始顺序。"""
    return sorted(urls, key=lambda u: _get_url_priority(u, url_priority), reverse=True)


def _download_video(
    video_id: str,
    play_urls: list[str],
    download_dir: str,
    url_priority: dict[str, int] | None = None,
    extra_headers: dict[str, str] | None = None,
) -> str:
    """遍历 play_urls，使用 httpx 流式下载视频到 download_dir。

    返回下载成功的本地文件路径。
    """
    if url_priority:
        play_urls = _sort_urls_by_priority(play_urls, url_priority)

    dir_path = Path(download_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    dest = dir_path / f"{video_id}.mp4"

    for i, url in enumerate(play_urls):
        try:
            logger.info("下载尝试 ({}/{}): video_id={}", i + 1, len(play_urls), video_id)
            with httpx.stream(
                "GET", url, timeout=120.0, follow_redirects=True,
                headers=extra_headers,
            ) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as f:
                    for chunk in resp.iter_bytes(chunk_size=65536):
                        f.write(chunk)
            size_mb = dest.stat().st_size / (1024 * 1024)
            logger.info("下载完成: video_id={}, size={:.1f}MB", video_id, size_mb)
            return str(dest)
        except Exception as e:
            logger.warning("下载失败 ({}/{}): video_id={}, error={}", i + 1, len(play_urls), video_id, e)
            if dest.exists():
                dest.unlink()

    raise RuntimeError(f"所有下载地址均失败: video_id={video_id}")


def _download_via_ytdlp(
    video_id: str,
    source_url: str,
    download_dir: str,
) -> str:
    """用 yt-dlp 下载视频（自动处理音视频分离的 DASH 格式并合并）。"""
    output_template = str(Path(download_dir) / "%(id)s.%(ext)s")
    logger.info("yt-dlp 下载: video_id={}, url={}", video_id, source_url[:80])

    try:
        result = subprocess.run(
            [
                "yt-dlp",
                "-f", "bestvideo+bestaudio/best",
                "--merge-output-format", "mp4",
                "-o", output_template,
                "--no-playlist",
                source_url,
            ],
            capture_output=True,
            text=True,
            timeout=600,
        )
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"yt-dlp 下载超时: {source_url}")

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp 下载失败: {result.stderr.strip()[-500:]}")

    dest = Path(download_dir) / f"{video_id}.mp4"
    if not dest.exists():
        raise RuntimeError(f"yt-dlp 下载后文件未找到: {dest}")

    size_mb = dest.stat().st_size / (1024 * 1024)
    logger.info("yt-dlp 下载完成: video_id={}, size={:.1f}MB", video_id, size_mb)
    return str(dest)


def handle_download(task: Task, config: AppConfig) -> dict[str, Any]:
    """Download worker 的业务 handler。

    - source="manual": 用 yt-dlp 下载（处理 B站 等平台的 DASH 音视频分离）
    - source="subscription": 用 httpx 直链下载（TikTok 管道）
    """
    download_dir = config.download_worker.download_dir

    # 如果文件已存在，跳过下载
    expected_path = Path(download_dir) / f"{task.video_id}.mp4"
    if expected_path.exists() and expected_path.stat().st_size > 0:
        logger.info("视频已存在，跳过下载: video_id={}", task.video_id)
        return {"video_file": str(expected_path)}

    # manual 任务：用 yt-dlp 下载（处理 DASH 合并）
    if task.source == "manual":
        source_url = task.inputs.get("play_urls", [None])[0]
        if not source_url:
            raise RuntimeError("manual 任务未提供 source_url")
        video_file = _download_via_ytdlp(
            task.video_id, source_url, download_dir,
        )
        return {"video_file": video_file}

    # subscription 任务：用 httpx 直链下载（TikTok）
    play_urls = task.inputs.get("play_urls", [])
    if not play_urls:
        raise RuntimeError("Task inputs 中无 play_urls")

    download_headers = task.inputs.get("download_headers") or {}
    video_file = _download_video(
        task.video_id, play_urls, download_dir,
        url_priority=config.download_worker.url_priority,
        extra_headers=download_headers or None,
    )
    return {"video_file": video_file}


def run_download_worker(config_path: str = "config.yaml") -> None:
    """启动 download worker。"""
    run_worker("download", handle_download, config_path)


if __name__ == "__main__":
    run_download_worker()
