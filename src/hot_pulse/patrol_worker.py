"""巡检 Worker — 定时扫描飞书表格中的僵尸/失败任务并恢复执行。

直接调用 pipeline 函数恢复任务，不依赖 ZMQ。
作为独立进程运行：python -m hot_pulse.patrol_worker
"""

from __future__ import annotations

import signal
import sys
import time
from datetime import datetime
from typing import Any

from loguru import logger

from hot_pulse.config import AppConfig, load_config
from hot_pulse.feishu import FeishuClient, _record_to_task
from hot_pulse.pipeline import (
    STATUS_TO_STAGE,
    run_manual_pipeline,
    run_subscription_pipeline,
)
from hot_pulse.task_manager import STAGE_MAPPING


# ---------------------------------------------------------------------------
# 僵尸检测
# ---------------------------------------------------------------------------


def _is_zombie(fields: dict, start_field: str, threshold_minutes: int) -> bool:
    """检查 start_field 时间戳是否超过阈值。"""
    start_ts = fields.get(start_field, 0)
    if isinstance(start_ts, (int, float)) and start_ts > 0:
        start_time = datetime.fromtimestamp(start_ts / 1000)
        elapsed = (datetime.now() - start_time).total_seconds() / 60
        return elapsed > threshold_minutes
    # 无时间戳也视为僵尸（异常状态）
    return True


# ---------------------------------------------------------------------------
# 飞书查询
# ---------------------------------------------------------------------------


def _query_records_by_status(
    feishu: FeishuClient, status: str
) -> list[tuple[str, dict]]:
    """查询飞书表格中指定状态的记录，返回 (record_id, fields) 列表。"""
    feishu._ensure_token()
    url = (
        f"https://open.feishu.cn/open-apis/bitable/v1/apps/{feishu._app_token}"
        f"/tables/{feishu._table_id}/records/search"
    )

    all_items: list[tuple[str, dict]] = []
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
        for item in items:
            record_id = item.get("record_id", "")
            fields = item.get("fields", {})
            if record_id and fields:
                all_items.append((record_id, fields))

        page_token = data.get("data", {}).get("page_token")
        if not page_token:
            break

    return all_items


# ---------------------------------------------------------------------------
# 巡检逻辑
# ---------------------------------------------------------------------------


def run_patrol(config: AppConfig) -> int:
    """执行一轮巡检。返回恢复的任务数。"""
    feishu = FeishuClient(config)
    threshold = config.patrol_worker.zombie_threshold_minutes
    recovered = 0

    try:
        # STATUS_TO_STAGE 去重迭代：同一 stage 可能对应多个状态
        seen_stages: set[str] = set()
        for status, stage in STATUS_TO_STAGE.items():
            if stage in seen_stages:
                continue
            seen_stages.add(stage)

            cfg = STAGE_MAPPING.get(stage)
            if cfg is None:
                continue

            items = _query_records_by_status(feishu, status)
            if not items:
                continue

            logger.info("状态 '{}' → stage={} 查到 {} 条记录", status, stage, len(items))

            for record_id, fields in items:
                # running 状态需要检查是否超时
                is_fail = "失败" in status
                if not is_fail and not _is_zombie(fields, cfg.start_field, threshold):
                    continue

                # 回退飞书状态 → init_status
                try:
                    feishu.update_record(record_id, {"状态": cfg.init_status})
                    logger.info(
                        "回退: record_id={}, '{}' → '{}'",
                        record_id, status, cfg.init_status,
                    )
                except Exception as exc:
                    logger.warning("飞书回退失败: record_id={}, error={}", record_id, exc)
                    continue

                # 构造 Task 并调用 pipeline
                task = _record_to_task(fields, record_id, stage)
                if task is None:
                    logger.warning("无法构造 Task: record_id={}", record_id)
                    continue

                try:
                    if task.source == "manual":
                        run_manual_pipeline(task, config, start_stage=stage)
                    else:
                        run_subscription_pipeline(task, config, start_stage=stage)
                    logger.info("恢复完成: video_id={}, stage={}", task.video_id, stage)
                except Exception as exc:
                    logger.error(
                        "pipeline 恢复失败: video_id={}, stage={}, error={}",
                        task.video_id, stage, exc,
                    )

                recovered += 1
    finally:
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


def main() -> None:
    """CLI 入口: 启动巡检 Worker 主循环。"""
    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="{time:HH:mm:ss} | {level} | <light-black>[patrol]</light-black> {message}")

    main_loop()


if __name__ == "__main__":
    main()
