"""knowledge_worker — 通用知识整理 Worker。

Pull ZMQ 5557，读取转写文本，调用 LLM 提炼结构化知识笔记，
写入 Obsidian vault 的 00-Inbox/ 目录。
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from loguru import logger

from hot_pulse.analyze_worker import _call_llm_api
from hot_pulse.config import AppConfig
from hot_pulse.task import Task

# ---------------------------------------------------------------------------
# 内置默认 Prompt
# ---------------------------------------------------------------------------

_DEFAULT_KNOWLEDGE_PROMPT = """\
你是一位专业的知识管理助手。请根据以下视频的转写文本，提炼一份结构化的知识笔记。

必须严格按以下格式输出：

## 一句话总结
（用1-2句话概括视频核心内容）

## 所属领域
（按层级格式标注所属领域，如：**AI / 深度学习 / 自然语言处理**）

## 关键概念
（列出3-8个关键概念，每个概念用一句话定义：
- **概念名**: 定义和解释）
格式参考：
- **Attention 机制**: 通过计算输入序列中每个元素对其他元素的注意力权重，实现动态的上下文感知表示。

## 要点
（列出3-8条核心要点，编号列表格式）

## 行动计划
（列出2-5条行动建议，格式如：- [ ] 阅读相关论文 xxx）

## 标签
（用 #tag 格式输出5-10个相关标签，每行3-4个）
"""


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def handle_knowledge(task: Task, config: AppConfig) -> dict[str, Any]:
    """Knowledge worker 的业务 handler。"""
    text_file = task.inputs.get("text_file")
    if not text_file:
        raise RuntimeError("Task inputs 中无 text_file")

    path = Path(text_file)
    if not path.exists():
        raise RuntimeError(f"转写文本文件不存在: {text_file}")

    text = _read_text_file(path)
    logger.info("读取转写文本: video_id={}, chars={}", task.video_id, len(text))

    if len(text.strip()) < 20:
        raise RuntimeError(f"转写文本内容过短: chars={len(text.strip())}")

    # 用 knowledge_worker 的 prompt（空则用内置默认）
    prompt = config.knowledge_worker.prompt or _DEFAULT_KNOWLEDGE_PROMPT
    # model 为空时复用 analyze_worker 的 model
    saved_model = config.analyze_worker.model
    if config.knowledge_worker.model:
        config.analyze_worker.model = config.knowledge_worker.model

    try:
        response = _call_llm_api(text, config)
    finally:
        config.analyze_worker.model = saved_model

    # 生成笔记
    vault = config.knowledge_worker.obsidian_vault
    inbox_dir = Path(vault) / "00-Inbox"
    inbox_dir.mkdir(parents=True, exist_ok=True)

    note_content = _build_note(task, response)
    safe_title = _sanitize_filename(task.title)
    note_file = inbox_dir / f"{safe_title}.md"
    note_file.write_text(note_content, encoding="utf-8")

    logger.info("知识笔记已保存: video_id={}, file={}", task.video_id, note_file)
    return {"obsidian_note": str(note_file)}


# ---------------------------------------------------------------------------
# 笔记格式化
# ---------------------------------------------------------------------------


def _build_note(task: Task, llm_response: str) -> str:
    """组装完整 Obsidian Markdown 笔记：YAML frontmatter + LLM 正文。"""
    now = datetime.now().strftime("%Y-%m-%d")

    frontmatter = f"""---
title: "{task.title}"
source: "{task.inputs.get('play_urls', [''])[0] if task.inputs.get('play_urls') else ''}"
creator: "{task.creator}"
platform: {task.platform}
created: {now}
status: inbox
---

# {task.title}

"""

    return frontmatter + llm_response.strip() + "\n"


def _read_text_file(path: Path) -> str:
    """读取文本文件，自动尝试多种编码。"""
    for encoding in ("utf-8", "gbk", "gb18030", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法识别文件编码: {path}")


def _sanitize_filename(name: str) -> str:
    """移除文件名中的非法字符。"""
    import re
    return re.sub(r'[\\/:*?"<>|]', "", name)


# ---------------------------------------------------------------------------
# CLI 入口
# ---------------------------------------------------------------------------
