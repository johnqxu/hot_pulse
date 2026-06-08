from __future__ import annotations

import json
import time
from typing import Any

import httpx
from loguru import logger

from hot_pulse.config import AppConfig
from hot_pulse.models import VideoRecord, record_to_fields
from hot_pulse.task import Task

_FEISHU_BASE = "https://open.feishu.cn/open-apis"


def _extract_text(value: Any) -> str:
    """从飞书字段值中提取文本。

    飞书返回的文本字段格式为 [{"text": "xxx", "type": "text"}]，
    也可能是纯字符串。此函数统一处理。
    """
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return first.get("text", "")
        return str(first)
    return ""


# 各阶段从飞书记录中提取 inputs 的字段映射
_STAGE_INPUT_MAP: dict[str, dict[str, str]] = {
    "download": {"play_urls": "视频链接"},
    "extract_audio": {"video_file": "视频文件地址"},
    "transcribe": {"audio_file": "音频文件地址"},
    "analyze": {"text_file": "文字文件地址"},
    "knowledge": {"text_file": "文字文件地址"},
    "dingtalk_push": {"report_file": "分析报告地址"},
}


def _record_to_task(fields: dict, record_id: str, task_type: str) -> Task | None:
    """将飞书记录转换为 Task 对象。"""
    import uuid

    video_id = _extract_text(fields.get("视频ID", ""))
    if not video_id:
        return None

    creator = _extract_text(fields.get("博主", ""))
    title = _extract_text(fields.get("任务名", ""))
    platform = _extract_text(fields.get("平台", "")) or "抖音"
    source = _extract_text(fields.get("来源", "")) or "subscription"

    # 构建 inputs
    inputs: dict[str, Any] = {}
    input_map = _STAGE_INPUT_MAP.get(task_type, {})
    for key, feishu_field in input_map.items():
        value = _extract_text(fields.get(feishu_field, ""))
        if value:
            if key == "play_urls":
                try:
                    inputs[key] = json.loads(value)
                except (json.JSONDecodeError, TypeError):
                    inputs[key] = [value]
            else:
                inputs[key] = value

    return Task(
        task_id=str(uuid.uuid4()),
        task_type=task_type,
        video_id=video_id,
        creator=creator,
        title=title,
        platform=platform,
        source=source,
        feishu_record_id=record_id,
        inputs=inputs,
    )


class FeishuClient:
    """飞书多维表格客户端。"""

    def __init__(self, config: AppConfig) -> None:
        self._app_id = config.secrets.feishu_app_id
        self._app_secret = config.secrets.feishu_app_secret
        self._app_token = config.feishu.bitable.app_token
        self._table_id = config.feishu.bitable.table_id
        self._client = httpx.Client(timeout=30.0)
        self._token: str = ""
        self._token_expires: float = 0.0

    def _ensure_token(self) -> None:
        """获取或刷新 tenant_access_token。"""
        if self._token and time.time() < self._token_expires:
            return

        resp = self._client.post(
            f"{_FEISHU_BASE}/auth/v3/tenant_access_token/internal",
            json={
                "app_id": self._app_id,
                "app_secret": self._app_secret,
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            raise RuntimeError(
                f"获取飞书 token 失败: {data.get('msg', '未知错误')}"
            )

        self._token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 7200) - 300
        self._client.headers["Authorization"] = f"Bearer {self._token}"
        logger.debug("飞书 tenant_access_token 已获取/刷新")

    def query_video_ids(self, creator_name: str) -> set[str]:
        """查询飞书表格中指定博主的已有视频 ID 集合。"""
        self._ensure_token()
        url = (
            f"{_FEISHU_BASE}/bitable/v1/apps/{self._app_token}"
            f"/tables/{self._table_id}/records/search"
        )

        all_ids: set[str] = set()
        page_token: str | None = None

        while True:
            body: dict = {
                "field_names": ["视频ID"],
                "filter": {
                    "conjunction": "and",
                    "conditions": [
                        {
                            "field_name": "博主",
                            "operator": "is",
                            "value": [creator_name],
                        }
                    ],
                },
                "page_size": 500,
            }
            if page_token:
                body["page_token"] = page_token

            resp = self._client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                logger.warning(f"飞书查询记录失败: {data.get('msg')}")
                return all_ids

            items = data.get("data", {}).get("items") or []
            for item in items:
                fields = item.get("fields", {})
                vid = _extract_text(fields.get("视频ID", ""))
                if vid:
                    all_ids.add(str(vid))

            page_token = data.get("data", {}).get("page_token")
            if not page_token:
                break

        logger.debug(f"飞书查询到 {len(all_ids)} 条已有记录 (博主={creator_name})")
        return all_ids

    def create_records(self, records: list[VideoRecord]) -> list[str]:
        """批量写入新视频记录到飞书表格，返回 record_id 列表。"""
        if not records:
            return []

        self._ensure_token()
        url = (
            f"{_FEISHU_BASE}/bitable/v1/apps/{self._app_token}"
            f"/tables/{self._table_id}/records/batch_create"
        )

        payload = {
            "records": [
                {"fields": record_to_fields(r)}
                for r in records
            ]
        }

        resp = self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            logger.error(f"飞书写入记录失败: {data.get('msg')} | 响应: {data}")
            return []

        created = data.get("data", {}).get("records") or []
        record_ids = [r["record_id"] for r in created if "record_id" in r]
        logger.info(f"飞书成功写入 {len(created)} 条记录")
        return record_ids

    def update_record(self, record_id: str, fields: dict) -> None:
        """按 record_id 更新单条飞书记录的部分字段。"""
        self._ensure_token()
        url = (
            f"{_FEISHU_BASE}/bitable/v1/apps/{self._app_token}"
            f"/tables/{self._table_id}/records/{record_id}"
        )

        resp = self._client.put(url, json={"fields": fields})
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            logger.warning("飞书更新记录失败: {} | record_id={}", data.get("msg"), record_id)
        else:
            logger.debug("飞书更新记录成功: record_id={}", record_id)

    def query_records_by_status(self, status: str, task_type: str) -> list[Task]:
        """按飞书表格"状态"字段查询记录，返回 Task 对象列表。"""
        self._ensure_token()
        url = (
            f"{_FEISHU_BASE}/bitable/v1/apps/{self._app_token}"
            f"/tables/{self._table_id}/records/search"
        )

        tasks: list[Task] = []
        page_token: str | None = None

        while True:
            body: dict = {
                "filter": {
                    "conjunction": "and",
                    "conditions": [
                        {
                            "field_name": "状态",
                            "operator": "is",
                            "value": [status],
                        }
                    ],
                },
                "page_size": 500,
            }
            if page_token:
                body["page_token"] = page_token

            resp = self._client.post(url, json=body)
            resp.raise_for_status()
            data = resp.json()

            if data.get("code") != 0:
                logger.warning("飞书按状态查询记录失败: {}", data.get("msg"))
                return tasks

            items = data.get("data", {}).get("items") or []
            for item in items:
                record_id = item.get("record_id", "")
                fields = item.get("fields", {})
                task = _record_to_task(fields, record_id, task_type)
                if task:
                    tasks.append(task)

            page_token = data.get("data", {}).get("page_token")
            if not page_token:
                break

        logger.info("飞书查询到 {} 条状态={} 的记录", len(tasks), status)
        return tasks

    def close(self) -> None:
        self._client.close()
