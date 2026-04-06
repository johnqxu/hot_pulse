from __future__ import annotations

import signal
from typing import Any, Callable

import zmq
from loguru import logger

from hot_pulse.config import AppConfig, load_config
from hot_pulse.feishu import FeishuClient
from hot_pulse.task import Task
from hot_pulse.task_manager import STAGE_MAPPING, TaskManager
from hot_pulse.zmq_client import ZmqConsumer, ZmqPublisher

WorkerHandler = Callable[[Task, AppConfig], dict[str, Any]]

_WORKER_COLORS: dict[str, str] = {
    "download": "cyan",
    "extract_audio": "yellow",
    "transcribe": "blue",
    "analyze": "magenta",
    "dingtalk_push": "red",
}


def _setup_worker_logger(task_type: str) -> None:
    """为 worker 子进程配置带颜色标识的日志。"""
    color = _WORKER_COLORS.get(task_type, "white")
    tag = task_type.replace("_", " ")
    logger.remove()
    logger.add(
        __import__("sys").stderr,
        level="INFO",
        format=f"{{time:HH:mm:ss}} | {{level}} | <{color}>[{tag}]</{color}> {{message}}",
    )


def run_worker(
    task_type: str,
    handler: WorkerHandler,
    config_path: str = "config.yaml",
) -> None:
    """启动通用 worker 主循环。

    Args:
        task_type: 该 worker 负责的 task_type，用于过滤收到的 Task
        handler: 业务处理回调，签名为 (Task, AppConfig) -> outputs dict
        config_path: 配置文件路径
    """
    config = load_config(config_path)
    _setup_worker_logger(task_type)
    worker_cfg = _get_worker_config(config, task_type)

    feishu = FeishuClient(config)
    tm = TaskManager(feishu)
    consumer = ZmqConsumer(worker_cfg.pull_endpoint)
    publisher = ZmqPublisher(worker_cfg.push_endpoint)

    shutting_down = False

    def _signal_handler(sig: int, frame: object) -> None:
        nonlocal shutting_down
        logger.info("收到信号 {}, 准备关闭...", sig)
        shutting_down = True

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("[{}] Worker 已启动: pull={}, push={}", task_type, worker_cfg.pull_endpoint, worker_cfg.push_endpoint)

    # 启动时从飞书恢复历史任务
    cfg = STAGE_MAPPING.get(task_type)
    if cfg:
        try:
            pending_tasks = feishu.query_records_by_status(cfg.init_status, task_type)
            for task in pending_tasks:
                if shutting_down:
                    break
                try:
                    tm.start(task)
                    outputs = handler(task, config)
                    tm.finish(task, outputs)

                    next_task = tm.build_next(task)
                    if next_task:
                        publisher.send_task(next_task)
                except Exception as e:
                    tm.fail(task, str(e))
            if pending_tasks:
                logger.info("[{}] 启动恢复: 处理了 {} 条历史任务", task_type, len(pending_tasks))
        except Exception as exc:
            logger.warning("[{}] 启动恢复查询失败: {}", task_type, exc)

    try:
        while not shutting_down:
            try:
                task = consumer.recv_task()
            except zmq.Again:
                # RCVTIMEO 超时，检查关闭标志后继续循环
                continue
            except Exception:
                break

            if task.task_type != task_type:
                logger.warning("[{}] 跳过非本类型任务: type={}, video_id={}", task_type, task.task_type, task.video_id)
                continue

            try:
                tm.start(task)
                outputs = handler(task, config)
                tm.finish(task, outputs)

                next_task = tm.build_next(task)
                if next_task:
                    publisher.send_task(next_task)

            except Exception as e:
                tm.fail(task, str(e))

    finally:
        consumer.close()
        publisher.close()
        feishu.close()
        logger.info("[{}] Worker 已关闭", task_type)


def _get_worker_config(config: AppConfig, task_type: str) -> Any:
    """根据 task_type 获取对应的 worker 配置。"""
    cfg_map = {
        "download": config.download_worker,
        "extract_audio": config.extract_audio_worker,
        "transcribe": config.transcribe_worker,
        "analyze": config.analyze_worker,
        "dingtalk_push": config.dingtalk_worker,
    }
    cfg = cfg_map.get(task_type)
    if cfg is None:
        raise ValueError(f"未知的 task_type: {task_type}")
    return cfg
