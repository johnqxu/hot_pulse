"""串行管道编排器 — 直接函数调用串联 worker 函数。"""

from __future__ import annotations

from typing import Any, Callable

from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.feishu import FeishuClient
from hot_pulse.task import Task
from hot_pulse.task_manager import TaskManager

WorkerHandler = Callable[[Task, AppConfig], dict[str, Any]]

# 管道阶段定义：按顺序排列
_SUB_STAGES = (
    ("download", "hot_pulse.download_worker", "handle_download"),
    ("extract_audio", "hot_pulse.extract_audio_worker", "handle_extract_audio"),
    ("transcribe", "hot_pulse.transcribe_worker", "handle_transcribe"),
    ("analyze", "hot_pulse.analyze_worker", "handle_analyze"),
    ("dingtalk_push", "hot_pulse.dingtalk_worker", "handle_dingtalk_push"),
)

_MANUAL_STAGES = (
    ("download", "hot_pulse.download_worker", "handle_download"),
    ("extract_audio", "hot_pulse.extract_audio_worker", "handle_extract_audio"),
    ("transcribe", "hot_pulse.transcribe_worker", "handle_transcribe"),
    ("knowledge", "hot_pulse.knowledge_worker", "handle_knowledge"),
)


def _resolve_handler(module_name: str, attr_name: str) -> WorkerHandler:
    """按 stage 定义的模块名和函数名动态查找 handler。"""
    import importlib

    mod = importlib.import_module(module_name)
    return getattr(mod, attr_name)


def _run_stages(
    task: Task,
    config: AppConfig,
    stages: tuple,
    start_stage: str = "",
) -> None:
    """串行执行管道阶段。start_stage 非空时跳过前面的 stage。"""
    feishu = FeishuClient(config)
    tm = TaskManager(feishu)
    skip = bool(start_stage)
    try:
        for stage_name, module_name, attr_name in stages:
            if skip:
                if stage_name != start_stage:
                    continue
                skip = False
            handler = _resolve_handler(module_name, attr_name)
            task.task_type = stage_name
            tm.start(task)
            outputs = handler(task, config)
            tm.finish(task, outputs)
            next_task = tm.build_next(task)
            if next_task:
                task = next_task
            else:
                break
    finally:
        feishu.close()


def run_subscription_pipeline(task: Task, config: AppConfig, start_stage: str = "") -> None:
    """subscription 管道: download → extract → transcribe → analyze → dingtalk_push。"""
    _run_stages(task, config, _SUB_STAGES, start_stage)


def run_manual_pipeline(task: Task, config: AppConfig, start_stage: str = "") -> None:
    """manual 管道: download → extract → transcribe → knowledge。"""
    _run_stages(task, config, _MANUAL_STAGES, start_stage)


# 飞书状态 → pipeline stage 恢复映射
_STATUS_TO_STAGE: dict[str, str] = {
    "新视频": "download",
    "视频下载中": "download",
    "音频提取中": "extract_audio",
    "文字转写中": "transcribe",
    "报告分析中": "analyze",
    "报告推送中": "dingtalk_push",
    "知识整理中": "knowledge",
}

# 非终端状态集合（需要恢复的）
_NON_TERMINAL_STATUSES = frozenset(_STATUS_TO_STAGE.keys())


def recover_interrupted_tasks(config: AppConfig) -> int:
    """启动时从飞书恢复所有中断任务，返回恢复数量。"""
    from hot_pulse.feishu import FeishuClient

    feishu = FeishuClient(config)
    tasks: list[Task] = []
    try:
        for status, stage in _STATUS_TO_STAGE.items():
            fetched = feishu.query_records_by_status(status, stage)
            tasks.extend(fetched)
    finally:
        feishu.close()

    if not tasks:
        logger.info("启动恢复: 无中断任务")
        return 0

    logger.info("启动恢复: 发现 {} 个中断任务", len(tasks))
    recovered = 0
    for task in tasks:
        start_stage = _STATUS_TO_STAGE.get(task.status, "")
        if not start_stage:
            continue
        try:
            logger.info("恢复任务: video_id={}, status={} → stage={}",
                        task.video_id, task.status, start_stage)
            if task.source == "manual":
                run_manual_pipeline(task, config, start_stage)
            else:
                run_subscription_pipeline(task, config, start_stage)
            recovered += 1
        except Exception as e:
            logger.error("恢复任务失败: video_id={}, error={}", task.video_id, e)

    logger.info("启动恢复完成: {}/{} 个任务已恢复", recovered, len(tasks))
    return recovered
