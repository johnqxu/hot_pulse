from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.task import Task

# ---------------------------------------------------------------------------
# 常量
# ---------------------------------------------------------------------------

SUMMARY_PATTERN = re.compile(r"^<<<SUMMARY>>>(.+?)<<<END>>>")

_DEFAULT_PROMPT = """\
你是一位专业的财经分析师。请根据以下抖音短视频的转写文本，生成一份结构化的投资分析报告。

报告必须严格按以下格式输出：

第一行必须是摘要行（用于文件命名）：
<<<SUMMARY>>>不超过10个字的中文摘要<<<END>>>

从第二行开始，按以下章节输出报告正文：

### 1. 内容摘要
（3-5句话概括视频核心内容，从金融投资视角分析其影响）

### 2. 推荐板块
（列出2-4个相关投资板块，每个板块包含：推荐原因、核心逻辑、风险等级）

### 3. 推荐个股
（分为A股推荐和港股推荐，每只个股包含：推荐原因、核心优势、风险提示）

### 4. 风险提示
（列出3-5条主要风险，每条含标题和说明）

### 5. 操作建议
（包含：投资策略、仓位建议、买入时机、止损/止盈、持仓周期）

### 6. 标签
（用 #标签 格式输出5-8个相关标签）

注意：
- 分析必须基于视频实际内容，不要凭空编造
- 个股推荐要具体到股票代码
- 风险提示要客观全面"""


# ---------------------------------------------------------------------------
# LLM API 调用
# ---------------------------------------------------------------------------

def _call_llm_api(text: str, config: AppConfig, prompt: str = "") -> str:
    """调用 OpenAI 兼容的 chat/completions 接口，返回完整响应文本。

    prompt 参数可选：传入时优先使用，否则回退到 config.analyze_worker.prompt。
    """
    api_key = config.secrets.openai_api_key if config.secrets else ""
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY 未配置，请在 .env 中设置")

    model = config.analyze_worker.model
    prompt = prompt or config.analyze_worker.prompt or _DEFAULT_PROMPT

    payload: dict[str, object] = {
        "model": model,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": text},
        ],
        "temperature": 0.7,
    }

    reasoning_effort = config.analyze_worker.reasoning_effort
    if reasoning_effort:
        payload["reasoning_effort"] = reasoning_effort

    extra_body = config.analyze_worker.extra_body
    if extra_body:
        payload.update(extra_body)

    url = f"{config.analyze_worker.openai_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    logger.info("调用 LLM API: url={}, model={}", url, model)

    with httpx.Client(timeout=300.0) as client:
        resp = client.post(url, json=payload, headers=headers)

    if resp.status_code != 200:
        raise RuntimeError(f"LLM API 调用失败: status={resp.status_code}, body={resp.text[:500]}")

    data = resp.json()
    content = data["choices"][0]["message"]["content"]
    logger.info("LLM API 响应成功: chars={}", len(content))
    return content


# ---------------------------------------------------------------------------
# 响应解析
# ---------------------------------------------------------------------------

def _parse_response(response: str, fallback_title: str) -> tuple[str, str]:
    """从 LLM 响应中提取摘要和报告正文。

    Returns:
        (summary, report_body): 摘要不超过 10 个汉字，正文不含摘要行。
    """
    lines = response.strip().split("\n", 1)
    first_line = lines[0].strip()

    match = SUMMARY_PATTERN.match(first_line)
    if match:
        summary = match.group(1).strip()[:10]
        body = lines[1].strip() if len(lines) > 1 else ""
    else:
        # 兜底：使用视频标题截断
        summary = fallback_title[:10]
        body = response.strip()
        logger.warning("摘要提取失败，使用标题截断兜底: {}", summary)

    return summary, body


# ---------------------------------------------------------------------------
# 报告构建
# ---------------------------------------------------------------------------

def _build_report(task: Task, report_body: str) -> str:
    """组装完整 Markdown 报告：YAML frontmatter + 元信息头 + LLM 报告正文。"""
    now = datetime.now()
    analysis_time = now.strftime("%Y-%m-%d %H:%M:%S")

    # 视频发布时间：使用任务创建时间作为近似值
    create_time = task.created_at or now.strftime("%Y-%m-%d %H:%M:%S")
    if "T" in create_time:
        create_time = create_time[:19].replace("T", " ")

    # YAML 安全处理 title 中的引号
    safe_title = task.title.replace('"', '\\"')

    frontmatter = f"""\
---
video_id: {task.video_id}
platform: {task.platform}
creator: {task.creator}
title: "{safe_title}"
create_time: {create_time}
analysis_time: {analysis_time}
tags: [财经, 市场分析, 投资建议]
---"""

    header = f"""\
# {task.title}

**平台**: {task.platform}
**创作者**: {task.creator}
**发布时间**: {create_time}
**分析时间**: {analysis_time}

---"""

    return f"{frontmatter}\n\n{header}\n\n{report_body}\n"


# ---------------------------------------------------------------------------
# 文件名处理
# ---------------------------------------------------------------------------

_ILLEGAL_CHARS = re.compile(r'[\\/:*?"<>|]')


def _sanitize_filename(name: str) -> str:
    """移除文件名中的非法字符。"""
    return _ILLEGAL_CHARS.sub("", name)


# ---------------------------------------------------------------------------
# Analyze handler
# ---------------------------------------------------------------------------

def _read_text_file(path: Path) -> str:
    """读取文本文件，自动尝试多种编码。"""
    for encoding in ("utf-8", "gbk", "gb18030", "utf-16"):
        try:
            return path.read_text(encoding=encoding)
        except (UnicodeDecodeError, UnicodeError):
            continue
    raise ValueError(f"无法识别文件编码: {path}")


def _analyze(text_file: str, report_dir: str, task: Task, config: AppConfig) -> str:
    """读取转写文本 → 调用 LLM API → 保存报告文件。"""
    # 读取转写文本（多编码回退）
    path = Path(text_file)
    text = _read_text_file(path)
    logger.info("读取转写文本: video_id={}, chars={}", task.video_id, len(text))

    # 验证文本长度
    if len(text.strip()) < 20:
        raise RuntimeError(f"转写文本内容过短或为空: chars={len(text.strip())}")

    # 调用 LLM API
    response = _call_llm_api(text, config)

    # 验证报告内容
    if len(response.strip()) < 50:
        raise RuntimeError(f"LLM 返回报告内容过短: chars={len(response.strip())}")

    # 解析摘要和报告正文
    summary, report_body = _parse_response(response, task.title)

    # 构建完整报告
    report_content = _build_report(task, report_body)

    # 生成文件名
    date_str = datetime.now().strftime("%Y%m%d")
    creator = _sanitize_filename(task.creator)
    summary_clean = _sanitize_filename(summary)
    filename = f"{date_str}-{creator}-{summary_clean}.md"

    # 保存报告
    dir_path = Path(report_dir)
    dir_path.mkdir(parents=True, exist_ok=True)

    report_file = dir_path / filename
    report_file.write_text(report_content, encoding="utf-8")

    logger.info("报告已保存: video_id={}, file={}", task.video_id, report_file)
    return str(report_file)


def handle_analyze(task: Task, config: AppConfig) -> dict[str, Any]:
    """Analyze worker 的业务 handler。"""
    text_file = task.inputs.get("text_file")
    if not text_file:
        raise RuntimeError("Task inputs 中无 text_file")

    path = Path(text_file)
    if not path.exists():
        raise RuntimeError(f"转写文本文件不存在: {text_file}")

    report_file = _analyze(
        text_file, config.analyze_worker.report_dir, task, config,
    )
    return {"report_file": report_file}
