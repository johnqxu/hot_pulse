"""ingest CLI — 手动提交视频内容到 Hot Pulse 处理管道。

用法:
    uv run hot-pulse-ingest \\
      --type video \\
      --platform bilibili \\
      --url "https://www.bilibili.com/video/BV1xxx" \\
      --title "可选标题" \\
      --notes "可选备注"

    或等价用法:
    uv run python -m hot_pulse ingest \\
      --type video \\
      --platform bilibili \\
      --url "https://www.bilibili.com/video/BV1xxx"
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from datetime import datetime

from loguru import logger

from hot_pulse.config import AppConfig, load_config
from hot_pulse.feishu import FeishuClient
from hot_pulse.models import VideoRecord
from hot_pulse.task import Task
from hot_pulse.pipeline import run_manual_pipeline

# ---------------------------------------------------------------------------
# 微信视频号链接解析
# ---------------------------------------------------------------------------

_WX_SPH_RE = __import__("re").compile(r"sph/([A-Za-z0-9]+)")


def _extract_weixin_export_id(url: str) -> str:
    """从微信视频号 sph 分享链接中提取 exportId。"""
    m = _WX_SPH_RE.search(url)
    if not m:
        raise RuntimeError(f"无法从链接提取微信视频号 exportId: {url}")
    return m.group(1)


# ---------------------------------------------------------------------------
# yt-dlp 解析（只解析元信息，不下载）
# ---------------------------------------------------------------------------


def _resolve_url(url: str) -> tuple[str, str]:
    """用 yt-dlp --dump-json 解析分享链接，返回 (video_id, title, uploader)。"""
    try:
        result = subprocess.run(
            [
                "yt-dlp", "--dump-json", "--no-playlist",
                "--add-header", "Referer: https://www.bilibili.com",
                "--add-header", "Origin: https://www.bilibili.com",
                "--user-agent",
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError:
        raise RuntimeError("yt-dlp 未安装，请运行: uv sync")
    except subprocess.TimeoutExpired:
        raise RuntimeError(f"yt-dlp 解析超时: {url}")

    if result.returncode != 0:
        raise RuntimeError(f"yt-dlp 解析失败: {result.stderr.strip()[-500:]}")

    info = json.loads(result.stdout)
    vid = info.get("id", "")
    title = info.get("title", "") or info.get("fulltitle", "")
    uploader = info.get("uploader", "") or info.get("channel", "")
    return vid, title, uploader


# ---------------------------------------------------------------------------
# Task 构造
# ---------------------------------------------------------------------------


def _build_task(
    platform: str,
    video_id: str,
    title: str,
    uploader: str,
    source_url: str,
    notes: str,
    feishu_record_id: str,
) -> Task:
    """构造 Task(source="manual") 接入标准管道。"""
    task = Task(
        task_id=str(uuid.uuid4()),
        task_type="download",
        video_id=video_id,
        creator=uploader,
        title=title,
        platform=platform,
        source="manual",
        feishu_record_id=feishu_record_id,
        inputs={
            "play_urls": [source_url],
            "notes": notes or "",
        },
    )
    task.touch()
    return task


# ---------------------------------------------------------------------------
# 飞书记录
# ---------------------------------------------------------------------------


def _now_ms() -> int:
    return int(datetime.now().timestamp() * 1000)


def _create_feishu_record(
    feishu: FeishuClient,
    platform: str,
    video_id: str,
    title: str,
    uploader: str,
    source_url: str,
) -> str:
    try:
        record = VideoRecord(
            任务名=title,
            博主=uploader,
            平台=platform,
            视频ID=video_id,
            视频链接=json.dumps([source_url], ensure_ascii=False),
            视频发现时间=_now_ms(),
            来源="manual",
            last_update_time=_now_ms(),
        )
        record_ids = feishu.create_records([record])
        if record_ids:
            return record_ids[0]
    except Exception as e:
        logger.warning("飞书记录创建失败: {}", e)
    return ""


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="手动提交视频内容到 Hot Pulse 处理管道")
    parser.add_argument("--type", required=True, choices=["video"])
    parser.add_argument("--platform", required=True, choices=["bilibili", "weixin"])
    parser.add_argument("--url", required=True, help="视频分享链接")
    parser.add_argument("--title", default="", help="可选标题")
    parser.add_argument("--notes", default="", help="可选备注")
    args = parser.parse_args()

    try:
        config = load_config()
    except Exception as e:
        print(f"配置加载失败: {e}", file=sys.stderr)
        sys.exit(1)

    # 1. 按 platform 解析元信息
    weixin_fields: dict = {}
    if args.platform == "weixin":
        from hot_pulse.tikhub import TikHubClient
        tikhub = TikHubClient(config)
        detail = tikhub.fetch_weixin_video_detail(_extract_weixin_export_id(args.url))
        video_id = detail["video_id"]
        yt_title = detail["title"]
        uploader = detail["uploader"]
        weixin_fields = {
            "encrypted_url": detail["encrypted_url"],
            "url_token": detail["url_token"],
            "decode_key": detail["decode_key"],
        }
        tikhub.close()
    else:
        video_id, yt_title, uploader = _resolve_url(args.url)
    title = args.title or yt_title

    # 2. 飞书记录
    feishu_record_id = ""
    try:
        feishu = FeishuClient(config)
        feishu_record_id = _create_feishu_record(
            feishu, args.platform, video_id, title, uploader, args.url,
        )
        if feishu_record_id:
            logger.info("飞书记录已创建: record_id={}", feishu_record_id)
        feishu.close()
    except Exception as e:
        logger.warning("FeishuClient 初始化失败: {}", e)

    # 3. 构造 Task
    task_inputs: dict = {
        "play_urls": [args.url],
        "notes": args.notes or "",
    }
    task_inputs.update(weixin_fields)
    task = _build_task(
        platform=args.platform,
        video_id=video_id,
        title=title,
        uploader=uploader,
        source_url=args.url,
        notes=args.notes,
        feishu_record_id=feishu_record_id,
    )
    # 注入 weixin 专属字段
    task.inputs.update(weixin_fields)

    # 4. 串行执行管道: download → extract → transcribe → knowledge
    run_manual_pipeline(task, config)


if __name__ == "__main__":
    main()
