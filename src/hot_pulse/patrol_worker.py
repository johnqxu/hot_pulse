from __future__ import annotations

import signal
import sys
import time
import uuid
from datetime import datetime
from typing import Any

import zmq
from loguru import logger

from hot_pulse.config import AppConfig, load_config
from hot_pulse.feishu import FeishuClient, _extract_text
from hot_pulse.task import Task
from hot_pulse.task_manager import STAGE_MAPPING


# ---------------------------------------------------------------------------
# 反向映射：running_status / fail_status → (task_type, init_status, start_field)
# ---------------------------------------------------------------------------

_StageReverse = tuple[str, str, str]  # (task_type, init_status, start_field)


def _build_reverse_map() -> dict[str, _StageReverse]:
    """从 STAGE_MAPPING 构建 running/fail status 的反向索引。"""
    result: dict[str, _StageReverse] = {}
    for task_type, cfg in STAGE_MAPPING.items():
        result[cfg.running_status] = (task_type, cfg.init_status, cfg.start_field)
        result[cfg.fail_status] = (task_type, cfg.init_status, cfg.start_field)
    return result


STAGE_REVERSE = _build_reverse_map()


# ---------------------------------------------------------------------------
# ZMQ 路由：task_type → PUSH socket
# ---------------------------------------------------------------------------

def _build_push_routes(config: AppConfig) -> dict[str, zmq.Socket]:
    """为每种 task_type 创建 PUSH socket 连接到对应 worker 的 pull_endpoint。"""
    ctx = zmq.Context()
    routes: dict[str, zmq.Socket] = {
        "download": config.download_worker.pull_endpoint,
        "extract_audio": config.extract_audio_worker.pull_endpoint,
        "transcribe": config.transcribe_worker.pull_endpoint,
        "analyze": config.analyze_worker.pull_endpoint,
        "dingtalk_push": config.dingtalk_worker.pull_endpoint,
    }
    sockets: dict[str, zmq.Socket] = {}
    for task_type, endpoint in routes.items():
        sock = ctx.socket(zmq.PUSH)
        sock.set_hwm(100)
        sock.connect(endpoint)
        sockets[task_type] = sock
        logger.info("PUSH socket 已连接: {} → {}", task_type, endpoint)
    return sockets


def _close_push_routes(sockets: dict[str, zmq.Socket]) -> None:
    for task_type, sock in sockets.items():
        sock.close(linger=1000)
    logger.info("所有 PUSH socket 已关闭")


# ---------------------------------------------------------------------------
# 巡检逻辑
# ---------------------------------------------------------------------------

def _query_records_by_status(feishu: FeishuClient, status: str) -> list[dict]:
    """查询飞书表格中指定状态的记录，返回原始字段列表。"""
    feishu._ensure_token()
    url = (
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{feishu._app_token}"
        f"/tables/{feishu._table_id}/records/search"
    )
    all_items: list[dict] = []
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

        resp = feishu._client.post(url, json=body)
        resp.raise_for_status()
        data = resp.json()

        if data.get("code") != 0:
            logger.warning("飞书查询失败: status={}, msg={}", status, data.get("msg"))
            return all_items

        items = data.get("data", {}).get("items") or []
        all_items.extend(items)

        page_token = data.get("data", {}).get("page_token")
        if not page_token:
            break

    return all_items


def _is_zombie(fields: dict, start_field: str, threshold_minutes: int) -> bool:
    """检查 start_field 时间戳是否超过阈值。"""
    start_ts = fields.get(start_field, 0)
    if isinstance(start_ts, (int, float)) and start_ts > 0:
        start_time = datetime.fromtimestamp(start_ts / 1000)
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        return elapsed > threshold_minutes
    # 无时间戳也视为僵尸（异常状态）
    return True


def _build_task_from_record(fields: dict, record_id: str, task_type: str) -> Task:
    """从飞书记录构造 Task 对象。"""
    from hot_pulse.feishu import _STAGE_INPUT_MAP

    video_id = _extract_text(fields.get("视频ID", ""))
    creator = _extract_text(fields.get("博主", ""))
    title = _extract_text(fields.get("任务名", ""))
    platform = _extract_text(fields.get("平台", "")) or "抖音"

    inputs: dict[str, Any] = {}
    input_map = _STAGE_INPUT_MAP.get(task_type, {})
    for key, feishu_field in input_map.items():
        value = _extract_text(fields.get(feishu_field, ""))
        if value:
            if key == "play_urls":
                import json
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
        feishu_record_id=record_id,
        inputs=inputs,
    )


def run_patrol(config: AppConfig) -> int:
    """执行一轮巡检。返回恢复的任务数。"""
    feishu = FeishuClient(config)
    sockets = _build_push_routes(config)
    threshold = config.patrol_worker.zombie_threshold_minutes
    recovered = 0

    try:
        for status, (task_type, init_status, start_field) in STAGE_REVERSE.items():
            is_running = status in {cfg.running_status for cfg in STAGE_MAPPING.values()}

            items = _query_records_by_status(feishu, status)
            if not items:
                continue

            logger.info("状态 '{}' 查到 {} 条记录", status, len(items))

            for item in items:
                record_id = item.get("record_id", "")
                fields = item.get("fields", {})

                # running 状态需要检查是否超时
                if is_running and not _is_zombie(fields, start_field, threshold):
                    continue

                # 回退飞书状态
                try:
                    feishu.update_record(record_id, {"状态": init_status})
                    logger.info(
                        "回退: record_id={}, '{}' → '{}'",
                        record_id, status, init_status,
                    )
                except Exception as exc:
                    logger.warning("飞书回退失败: record_id={}, error={}", record_id, exc)
                    continue

                # 构造 Task 并推送
                task = _build_task_from_record(fields, record_id, task_type)
                sock = sockets.get(task_type)
                if sock:
                    try:
                        sock.send(task.model_dump_json().encode("utf-8"), flags=zmq.NOBLOCK)
                        logger.info("推送: task_type={}, video_id={}", task_type, task.video_id)
                    except Exception as exc:
                        logger.warning("ZMQ 推送失败: task_type={}, error={}", task_type, exc)

                recovered += 1
    finally:
        _close_push_routes(sockets)
        feishu.close()

    return recovered


# ---------------------------------------------------------------------------
# 主循环
# ---------------------------------------------------------------------------

_shutting_down = False


def _signal_handler(sig: int, frame: object) -> None:
    global _shutting_down
    logger.info("收到信号 {}, 准备关闭...", sig)
    _shutting_down = True


def main_loop(config_path: str = "config.yaml") -> None:
    """巡检 worker 主循环。"""
    config = load_config(config_path)
    interval = config.patrol_worker.interval_minutes

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("巡检 Worker 已启动, 间隔={}min, 僵尸阈值={}min",
                interval, config.patrol_worker.zombie_threshold_minutes)

    while not _shutting_down:
        try:
            count = run_patrol(config)
            logger.info("本轮巡检完成, 恢复 {} 条任务", count)
        except Exception as exc:
            logger.error("巡检异常: {}", exc)

        # 分段 sleep 以响应关闭信号
        sleep_end = time.time() + interval * 60
        while time.time() < sleep_end and not _shutting_down:
            time.sleep(min(5, sleep_end - time.time()))

    logger.info("巡检 Worker 已关闭")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="{time:HH:mm:ss} | {level} | <light-black>[patrol]</light-black> {message}")

    main_loop()
