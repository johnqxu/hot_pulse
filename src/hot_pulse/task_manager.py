from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from hot_pulse.feishu import FeishuClient
from hot_pulse.task import Task


@dataclass(frozen=True)
class StageConfig:
    """单个阶段的飞书字段映射与路由配置。"""

    init_status: str
    running_status: str
    finish_status: str
    fail_status: str
    start_field: str
    end_field: str
    output_map: dict[str, str] = field(default_factory=dict)
    next_type: str | None = None
    next_input_map: dict[str, str] = field(default_factory=dict)


STAGE_MAPPING: dict[str, StageConfig] = {
    "download": StageConfig(
        init_status="新视频",
        running_status="视频下载中",
        finish_status="视频下载完成",
        fail_status="视频下载失败",
        start_field="视频下载开始时间",
        end_field="视频下载完成时间",
        output_map={"video_file": "视频文件地址"},
        next_type="extract_audio",
        next_input_map={"video_file": "video_file"},
    ),
    "extract_audio": StageConfig(
        init_status="视频下载完成",
        running_status="音频提取中",
        finish_status="音频提取完成",
        fail_status="音频提取失败",
        start_field="音频提取开始时间",
        end_field="音频提取完成时间",
        output_map={"audio_file": "音频文件地址"},
        next_type="transcribe",
        next_input_map={"audio_file": "audio_file"},
    ),
    "transcribe": StageConfig(
        init_status="音频提取完成",
        running_status="文字转写中",
        finish_status="文字转写完成",
        fail_status="文字转写失败",
        start_field="文字转写开始时间",
        end_field="文字转写完成时间",
        output_map={"text_file": "文字文件地址"},
        next_type="analyze",
        next_input_map={"text_file": "text_file"},
    ),
    "analyze": StageConfig(
        init_status="文字转写完成",
        running_status="报告分析中",
        finish_status="报告分析完成",
        fail_status="报告分析失败",
        start_field="内容分析开始时间",
        end_field="内容分析结束时间",
        output_map={"report_file": "分析报告地址"},
        next_type="dingtalk_push",
        next_input_map={"report_file": "report_file"},
    ),
    "dingtalk_push": StageConfig(
        init_status="报告分析完成",
        running_status="报告推送中",
        finish_status="报告推送完成",
        fail_status="报告推送失败",
        start_field="报告推送开始时间",
        end_field="报告推送完成时间",
        output_map={},
        next_type=None,
    ),
}


def _now_ms() -> int:
    """当前时间的 Unix 毫秒时间戳（飞书 datetime 字段要求）。"""
    from datetime import datetime

    return int(datetime.now().timestamp() * 1000)


class TaskManager:
    """封装任务在 start/finish/fail 状态流转时的飞书同步和日志输出。"""

    def __init__(self, feishu: FeishuClient) -> None:
        self._feishu = feishu

    def start(self, task: Task) -> Task:
        """标记任务开始运行，同步更新飞书开始时间和运行状态。"""
        task.status = "running"
        task.touch()

        cfg = STAGE_MAPPING.get(task.task_type)
        if cfg and task.feishu_record_id:
            try:
                self._feishu.update_record(
                    task.feishu_record_id,
                    {cfg.start_field: _now_ms(), "状态": cfg.running_status},
                )
            except Exception as exc:
                logger.warning("飞书更新开始时间失败: {}", exc)

        logger.info("[{}] 任务开始: video_id={}, title={}", task.task_type, task.video_id, task.title)
        return task

    def finish(self, task: Task, outputs: dict[str, Any]) -> Task:
        """标记任务完成，将 outputs 按阶段 output_map 写入飞书。"""
        task.status = "done"
        task.outputs.update(outputs)
        task.touch()
        cfg = STAGE_MAPPING.get(task.task_type)
        if cfg and task.feishu_record_id:
            fields: dict[str, Any] = {
                cfg.end_field: _now_ms(),
                "状态": cfg.finish_status,
            }
            for key, feishu_field in cfg.output_map.items():
                if key in outputs:
                    fields[feishu_field] = outputs[key]
            try:
                self._feishu.update_record(task.feishu_record_id, fields)
            except Exception as exc:
                logger.warning("飞书更新完成状态失败: {}", exc)

        logger.info("[{}] 任务完成: video_id={}", task.task_type, task.video_id)
        return task

    def fail(self, task: Task, error: str) -> Task:
        """标记任务失败，同步更新飞书错误状态。"""
        task.status = "failed"
        task.error = error
        task.touch()

        cfg = STAGE_MAPPING.get(task.task_type)
        fail_status = cfg.fail_status if cfg else "失败"
        if task.feishu_record_id:
            try:
                self._feishu.update_record(
                    task.feishu_record_id,
                    {"状态": fail_status},
                )
            except Exception as exc:
                logger.warning("飞书更新失败状态失败: {}", exc)

        logger.error("[{}] 任务失败: video_id={}, error={}", task.task_type, task.video_id, error)
        return task

    def build_next(self, task: Task) -> Task | None:
        """基于当前任务的 outputs 构造下一阶段 Task。最后一个阶段返回 None。"""
        cfg = STAGE_MAPPING.get(task.task_type)
        if cfg is None or cfg.next_type is None:
            return None
        inputs: dict[str, Any] = {}
        for src_key, dst_key in cfg.next_input_map.items():
            if src_key in task.outputs:
                inputs[dst_key] = task.outputs[src_key]
        next_task = Task(
            task_id=str(uuid.uuid4()),
            task_type=cfg.next_type,
            video_id=task.video_id,
            creator=task.creator,
            title=task.title,
            platform=task.platform,
            feishu_record_id=task.feishu_record_id,
            inputs=inputs,
        )
        next_task.touch()

        logger.info("[→{}] 构建下一阶段任务: video_id={}", cfg.next_type, task.video_id)
        return next_task
