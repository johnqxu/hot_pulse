from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Task(BaseModel):
    """流水线统一任务模型 — 内存消息信封，不持久化。"""

    # 身份标识
    task_id: str
    task_type: str  # "download" | "extract_audio" | "transcribe" | "analyze"

    # 源信息
    video_id: str
    creator: str
    title: str
    platform: str = "抖音"
    source: str = "subscription"  # "subscription" | "manual"
    feishu_record_id: str = ""

    # 阶段依赖与产出
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)

    # 状态
    status: str = "pending"  # pending | running | done | failed
    error: str = ""

    # 时间
    created_at: str = ""
    updated_at: str = ""

    def touch(self) -> None:
        """更新 updated_at 为当前时间。"""
        self.updated_at = datetime.now().isoformat()
