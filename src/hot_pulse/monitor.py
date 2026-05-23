from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from hot_pulse.config import load_config, AppConfig
from hot_pulse.feishu import FeishuClient
from hot_pulse.models import VideoInfo, VideoRecord, build_record
from hot_pulse.task import Task
from hot_pulse.tikhub import TikHubClient
from hot_pulse.zmq_client import ZmqPublisher


@dataclass
class MonitorResult:
    """单次监控运行结果。"""
    total_creators: int = 0
    success_creators: int = 0
    failed_creators: int = 0
    total_new_videos: int = 0
    errors: list[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.errors is None:
            self.errors = []


def run_monitor(config_path: str = "config.yaml") -> MonitorResult:
    """执行一轮监控：遍历所有创作者，检测新视频，写入飞书。

    Args:
        config_path: 配置文件路径，默认为项目根目录的 config.yaml

    Returns:
        MonitorResult 包含本轮监控的汇总结果
    """
    result = MonitorResult()

    logger.info("[monitor] 步骤1: 开始加载配置...")
    try:
        config = load_config(config_path)
    except (FileNotFoundError, ValueError) as e:
        logger.error(f"配置加载失败: {e}")
        result.errors.append(str(e))
        return result
    logger.info("[monitor] 步骤1: 配置加载完成, creators={}", len(config.creators))

    result.total_creators = len(config.creators)
    if not config.creators:
        logger.warning("未配置任何创作者，跳过监控")
        return result

    logger.info("[monitor] 步骤2: 初始化 TikHubClient...")
    try:
        tikhub = TikHubClient(config)
    except Exception as e:
        logger.error("[monitor] TikHubClient 初始化失败: {}", e)
        result.errors.append(str(e))
        return result
    logger.info("[monitor] 步骤2: TikHubClient 就绪")

    logger.info("[monitor] 步骤3: 初始化 FeishuClient...")
    try:
        feishu = FeishuClient(config)
    except Exception as e:
        logger.error("[monitor] FeishuClient 初始化失败: {}", e)
        result.errors.append(str(e))
        tikhub.close()
        return result
    logger.info("[monitor] 步骤3: FeishuClient 就绪")

    # ZMQ 发布者：仅在配置启用时创建
    zmq_pub: ZmqPublisher | None = None
    if config.zeromq.enabled:
        logger.info("[monitor] 步骤4: 初始化 ZMQ Publisher...")
        try:
            zmq_pub = ZmqPublisher(config.zeromq.push_endpoint)
            logger.info("[monitor] 步骤4: ZMQ Publisher 就绪")
        except Exception as e:
            logger.warning(f"ZMQ 初始化失败，将以仅飞书模式运行: {e}")

    logger.info("[monitor] 步骤5: 开始遍历 {} 个创作者", result.total_creators)
    try:
        for creator in config.creators:
            logger.info("[monitor] 处理创作者: {} (sec_uid={}...)", creator.name, creator.sec_uid[:20])
            try:
                new_count = _process_creator(
                    tikhub, feishu, zmq_pub, creator.name, creator.sec_uid
                )
                result.success_creators += 1
                result.total_new_videos += new_count
            except Exception as e:
                msg = f"处理创作者 {creator.name} 失败: {e}"
                logger.error(msg)
                result.failed_creators += 1
                result.errors.append(msg)
    finally:
        tikhub.close()
        feishu.close()
        if zmq_pub:
            zmq_pub.close()

    logger.info(
        f"监控完成: {result.success_creators}/{result.total_creators} 创作者成功, "
        f"共发现 {result.total_new_videos} 个新视频"
    )
    return result


def _process_creator(
    tikhub: TikHubClient,
    feishu: FeishuClient,
    zmq_pub: ZmqPublisher | None,
    creator_name: str,
    sec_uid: str,
) -> int:
    """处理单个创作者：拉取视频、对比去重、写入新记录、发送ZMQ消息。返回新视频数量。"""
    logger.info(f"开始处理创作者: {creator_name}")

    # 1. 从 TikHub 拉取最新视频
    logger.info("[monitor] 即将调用 fetch_user_post_videos: sec_uid={}...", sec_uid[:20])
    videos = tikhub.fetch_user_post_videos(sec_uid)
    logger.info(f"TikHub 返回 {len(videos)} 条视频 (博主={creator_name})")

    if not videos:
        logger.info(f"博主 {creator_name} 无视频，跳过")
        return 0

    # 2. 查询飞书已有记录
    existing_ids = feishu.query_video_ids(creator_name)

    # 3. 计算差集
    new_videos = [v for v in videos if v.video_id not in existing_ids]

    if not new_videos:
        logger.info(f"博主 {creator_name} 无新视频")
        return 0

    logger.info(f"博主 {creator_name} 发现 {len(new_videos)} 个新视频")

    # 4. 构建记录并写入飞书
    records: list[VideoRecord] = [build_record(v, creator_name) for v in new_videos]
    record_ids = feishu.create_records(records)

    # 5. 通过 ZMQ 发送 Task 消息
    if zmq_pub:
        for i, video in enumerate(new_videos):
            record_id = record_ids[i] if i < len(record_ids) else ""
            _send_zmq_task(zmq_pub, video, creator_name, record_id)

    return len(new_videos)


def _send_zmq_task(
    zmq_pub: ZmqPublisher,
    video: VideoInfo,
    creator_name: str,
    feishu_record_id: str,
) -> None:
    """构造 Task 对象并通过 ZMQ 发送，失败时记录日志但不阻塞主流程。"""
    task = Task(
        task_id=str(uuid.uuid4()),
        task_type="download",
        video_id=video.video_id,
        creator=creator_name,
        title=video.title,
        source="subscription",
        feishu_record_id=feishu_record_id,
        inputs={"play_urls": video.play_urls or []},
    )
    task.touch()
    try:
        zmq_pub.send_task(task)
    except Exception as e:
        logger.warning(f"ZMQ Task 发送失败 (video_id={video.video_id}): {e}")


if __name__ == "__main__":
    from loguru import logger as _logger
    import sys

    _logger.remove()
    _logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | <bold>[monitor]</bold> {message}")

    result = run_monitor()

    if result.errors:
        print(f"\n--- 错误汇总 ---")
        for err in result.errors:
            print(f"  - {err}")

    print(
        f"\n--- 监控结果 ---\n"
        f"  创作者: {result.success_creators}/{result.total_creators} 成功"
        f" ({result.failed_creators} 失败)\n"
        f"  新视频: {result.total_new_videos} 个"
    )
