from __future__ import annotations

import base64
import hashlib
import hmac
import re
import time
import urllib.parse
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.task import Task

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

_LAST_SEND_TIME: float = 0.0

_FRONTMATTER_RE = re.compile(r"^---\n.*?\n---\n", re.DOTALL)


def _strip_frontmatter(text: str) -> str:
    """移除 Markdown 文件顶部的 YAML frontmatter。"""
    return _FRONTMATTER_RE.sub("", text)


# ---------------------------------------------------------------------------
# 钉钉 Webhook 加签
# ---------------------------------------------------------------------------

def _sign_url(webhook_url: str, secret: str) -> str:
    """使用 HMAC-SHA256 加签构造完整的 Webhook URL。"""
    timestamp = str(round(time.time() * 1000))
    string_to_sign = f"{timestamp}\n{secret}"
    hmac_code = hmac.new(
        secret.encode("utf-8"),
        string_to_sign.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
    return f"{webhook_url}&timestamp={timestamp}&sign={sign}"


# ---------------------------------------------------------------------------
# 钉钉消息发送
# ---------------------------------------------------------------------------

def _send_dingtalk_message(
    webhook_url: str,
    secret: str,
    title: str,
    text: str,
) -> None:
    """构造 Markdown 消息并发送到钉钉 Webhook。"""
    url = _sign_url(webhook_url, secret)

    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": title,
            "text": text,
        },
    }

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(url, json=payload)

    if resp.status_code != 200:
        raise RuntimeError(f"钉钉 Webhook 请求失败: status={resp.status_code}, body={resp.text[:500]}")

    data = resp.json()
    errcode = data.get("errcode", -1)
    if errcode != 0:
        raise RuntimeError(f"钉钉 Webhook 返回错误: errcode={errcode}, errmsg={data.get('errmsg', '')}")

    logger.info("钉钉消息发送成功: title={}", title)


# ---------------------------------------------------------------------------
# 流控
# ---------------------------------------------------------------------------

def _wait_for_rate_limit(min_interval: int) -> None:
    """等待至距上次发送满 min_interval 秒。"""
    global _LAST_SEND_TIME
    now = time.time()
    elapsed = now - _LAST_SEND_TIME
    if elapsed < min_interval:
        wait = min_interval - elapsed
        logger.info("流控等待: {:.0f}s", wait)
        time.sleep(wait)
    _LAST_SEND_TIME = time.time()


# ---------------------------------------------------------------------------
# DingTalk handler
# ---------------------------------------------------------------------------

def handle_dingtalk_push(task: Task, config: AppConfig) -> dict[str, Any]:
    """DingTalk push worker 的业务 handler。"""
    report_file = task.inputs.get("report_file")
    if not report_file:
        raise RuntimeError("Task inputs 中无 report_file")

    path = Path(report_file)
    if not path.exists():
        raise RuntimeError(f"报告文件不存在: {report_file}")

    webhook_url = config.dingtalk_worker.webhook_url
    secret = config.secrets.dingtalk_secret if config.secrets else ""
    if not webhook_url:
        raise RuntimeError("dingtalk_worker.webhook_url 未配置")
    if not secret:
        raise RuntimeError("DINGTALK_SECRET 未配置，请在 .env 中设置")

    report_text = path.read_text(encoding="utf-8")
    report_text = _strip_frontmatter(report_text)

    # 流控等待
    _wait_for_rate_limit(config.dingtalk_worker.min_interval)

    # 发送钉钉消息
    # 钉钉 markdown 消息 title 为必填字段，task.title 可能为空，兜底用 creator
    dingtalk_title = task.title or f"{task.creator} 视频分析报告"
    _send_dingtalk_message(webhook_url, secret, dingtalk_title, report_text)

    return {}


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
