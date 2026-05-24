"""Hot Pulse 主进程 - 单进程定时监控管道。"""

from __future__ import annotations

import signal
import sys
import time
from datetime import datetime

from loguru import logger

from hot_pulse.config import load_config
from hot_pulse.monitor import run_monitor
from hot_pulse.pipeline import recover_interrupted_tasks

# 时间窗口
_HOUR_START = 7
_HOUR_END = 24

_shutting_down = False


def _signal_handler(sig: int, frame: object) -> None:
    global _shutting_down
    logger.info("收到信号 {}, 准备关闭...", sig)
    _shutting_down = True


def _monitor_loop(interval_minutes: int) -> None:
    """monitor 定时调度循环：07:00-24:00 内每 interval_minutes 分钟执行一次。"""
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

        sleep_end = time.time() + interval_minutes * 60
        while time.time() < sleep_end and not _shutting_down:
            time.sleep(min(5, sleep_end - time.time()))


def main() -> None:
    config = load_config()
    interval = config.schedule.interval_minutes

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    logger.info("Hot Pulse 主进程启动")

    # 启动恢复：处理上次未完成的中间状态任务
    try:
        recovered = recover_interrupted_tasks(config)
        logger.info("启动恢复处理了 {} 个中断任务", recovered)
    except Exception as e:
        logger.error("启动恢复失败: {}", e)

    _monitor_loop(interval)

    logger.info("Hot Pulse 主进程已退出")


if __name__ == "__main__":
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | <green>[main]</green> {message}")

    main()
