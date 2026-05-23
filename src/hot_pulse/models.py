from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass
class VideoInfo:
    """TikHub 返回的单条视频信息。"""
    video_id: str
    title: str
    url: str
    play_urls: list[str] | None = None


@dataclass
class VideoRecord:
    """写入飞书多维表格的一条记录。"""
    # 阶段① — 监控发现时填写
    任务名: str
    优先级: str = "中"
    状态: str = "新视频"
    任务类型: str = "视频"
    任务创建时间: int = 0        # type=1001 自动生成，写入时跳过
    平台: str = "抖音"
    博主: str = ""
    视频链接: str = ""           # type=1 文本（JSON 数组字符串）
    视频发现时间: int = 0        # type=5 日期时间（毫秒时间戳）
    视频ID: str = ""
    来源: str = "subscription"   # subscription | manual

    # 阶段② — 视频下载
    视频下载开始时间: int = 0
    视频下载完成时间: int = 0
    视频文件地址: str = ""
    音频文件地址: str = ""

    # 阶段③ — 文字转写
    文字转写开始时间: int = 0
    文字转写完成时间: int = 0
    文字文件地址: str = ""

    # 阶段④ — 内容分析
    内容分析开始时间: int = 0
    内容分析结束时间: int = 0
    分析报告地址: str = ""

    # 阶段⑤ — 报告推送
    报告推送开始时间: int = 0
    报告推送完成时间: int = 0

    last_update_time: int = 0    # type=5 日期时间（毫秒时间戳）


# 飞书表格字段名 → VideoRecord 属性名 的映射
FEISHU_FIELD_MAP: dict[str, str] = {
    "任务名": "任务名",
    "优先级": "优先级",
    "状态": "状态",
    "任务类型": "任务类型",
    # "任务创建时间" 是 type=1001 自动生成，跳过
    "平台": "平台",
    "博主": "博主",
    "视频链接": "视频链接",
    "视频发现时间": "视频发现时间",
    "视频ID": "视频ID",
    "来源": "来源",
    "视频下载开始时间": "视频下载开始时间",
    "视频下载完成时间": "视频下载完成时间",
    "视频文件地址": "视频文件地址",
    "音频文件地址": "音频文件地址",
    "文字转写开始时间": "文字转写开始时间",
    "文字转写完成时间": "文字转写完成时间",
    "文字文件地址": "文字文件地址",
    "内容分析开始时间": "内容分析开始时间",
    "内容分析结束时间": "内容分析结束时间",
    "分析报告地址": "分析报告地址",
    "last_update_time": "last_update_time",
}

# type=5 的日期时间字段列表（值是毫秒时间戳）
_DATETIME_FIELDS = {
    "视频发现时间", "视频下载开始时间", "视频下载完成时间",
    "文字转写开始时间", "文字转写完成时间",
    "内容分析开始时间", "内容分析结束时间",
    "报告推送开始时间", "报告推送完成时间",
    "last_update_time",
}

def _now_ms() -> int:
    """当前时间的毫秒时间戳。"""
    return int(datetime.now().timestamp() * 1000)


def build_record(video: VideoInfo, creator_name: str) -> VideoRecord:
    """根据视频信息和创作者名称构建一条飞书记录。"""
    now_ms = _now_ms()
    play_urls_json = json.dumps(video.play_urls, ensure_ascii=False) if video.play_urls else "[]"
    return VideoRecord(
        任务名=video.title,
        博主=creator_name,
        视频链接=play_urls_json,
        视频发现时间=now_ms,
        视频ID=video.video_id,
        last_update_time=now_ms,
    )


def record_to_fields(record: VideoRecord) -> dict[str, Any]:
    """将 VideoRecord 转为飞书多维表格字段字典，仅包含非空字段。

    根据飞书字段类型进行格式转换：
    - type=5  日期时间: Unix 毫秒时间戳
    - type=1  文本: 字符串
    - type=3  单选: 字符串
    """
    fields: dict[str, Any] = {}
    for field_name, attr_name in FEISHU_FIELD_MAP.items():
        value = getattr(record, attr_name)
        if not value:
            continue

        if field_name in _DATETIME_FIELDS:
            # type=5: 毫秒时间戳
            fields[field_name] = value
        else:
            # type=1/3: 文本/单选
            fields[field_name] = value

    return fields
