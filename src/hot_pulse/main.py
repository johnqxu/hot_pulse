from __future__ import annotations

import signal
import subprocess
import sys
import time
from datetime import datetime

from loguru import logger

from hot_pulse.config import load_config
from hot_pulse.monitor import run_monitor

# Worker 启动顺序（按管道上下游排列）
_WORKERS = [
    "hot_pulse.download_worker",
    "hot_pulse.extract_audio_worker",
    "hot_pulse.transcribe_worker",
    "hot_pulse.analyze_worker",
    "hot_pulse.dingtalk_worker",
    "hot_pulse.patrol_worker",
]

# 时间窗口
_HOUR_START = 7
_HOUR_END = 24

# Worker 启动后等待秒数
_READY_WAIT = 30

# 子进程退出等待超时（秒）
_TERMINATE_TIMEOUT = 10


def _start_workers() -> list[subprocess.Popen]:
    """按顺序启动所有 worker 子进程，返回 Popen 列表。启动失败时终止已启动的进程并退出。"""
    procs: list[subprocess.Popen] = []
    for mod in _WORKERS:
        cmd = [sys.executable, "-m", mod]
        logger.info("启动 worker: {}", " ".join(cmd))
        try:
            proc = subprocess.Popen(cmd)
            procs.append(proc)
            logger.info("worker {} 已启动, pid={}", mod, proc.pid)
        except Exception as exc:
            logger.error("启动 worker {} 失败: {}", mod, exc)
            _terminate_all(procs)
            sys.exit(1)
    return procs


def _terminate_all(procs: list[subprocess.Popen]) -> None:
    """向所有子进程发送 terminate，等待退出，超时则 kill。"""
    for proc in procs:
        if proc.poll() is None:
            proc.terminate()
    for proc in procs:
        if proc.poll() is None:
            try:
                proc.wait(timeout=_TERMINATE_TIMEOUT)
            except subprocess.TimeoutExpired:
                proc.kill()
                logger.warning("强制 kill 子进程 pid={}", proc.pid)


def _monitor_loop(interval_minutes: int) -> None:
    """monitor 定时调度循环：07:00-22:00 内每 interval_minutes 分钟执行一次。"""
    global _shutting_down
    while not _shutting_down:
        hour = datetime.now().hour
        if _HOUR_START <= hour < _HOUR_END:
            logger.info("开始执行 monitor (时间窗口内)")
            try:
                result = run_monitor()
                logger.info(
                    "monitor 完成: {} 个新视频, {}/{} 创作者成功",
                    result.total_new_videos,
                    result.success_creators,
                    result.total_creators,
                )
            except Exception as exc:
                logger.error("monitor 执行异常: {}", exc)
        else:
            logger.debug("当前时间 {} 点，不在调度窗口 ({}-{} 点)，跳过", hour, _HOUR_START, _HOUR_END)

        # 分段 sleep 以便及时响应关闭信号
        sleep_end = time.time() + interval_minutes * 60
        while time.time() < sleep_end and not _shutting_down:
            time.sleep(min(5, sleep_end - time.time()))


_shutting_down = False


def _signal_handler(sig: int, frame: object) -> None:
    global _shutting_down
    logger.info("收到信号 {}, 准备关闭...", sig)
    _shutting_down = True


def main() -> None:
    config = load_config()
    interval = config.schedule.interval_minutes

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("Hot Pulse 主进程启动")
    procs = _start_workers()

    logger.info("所有 worker 已启动，等待 {} 秒后开始 monitor 调度...", _READY_WAIT)
    _sleep_until = time.time() + _READY_WAIT
    while time.time() < _sleep_until and not _shutting_down:
        time.sleep(1)

    if not _shutting_down:
        _monitor_loop(interval)

    logger.info("正在关闭所有 worker 子进程...")
    _terminate_all(procs)
    logger.info("Hot Pulse 主进程已退出")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | <green>[main]</green> {message}")

    main()
