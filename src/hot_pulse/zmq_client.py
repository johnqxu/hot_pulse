from __future__ import annotations

import json

import zmq
from loguru import logger

from hot_pulse.task import Task


class ZmqPublisher:
    """ZMQ PUSH 客户端，用于向下游消费者发送任务消息。"""

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PUSH)
        self._socket.set_hwm(1000)
        self._socket.connect(endpoint)
        logger.debug(f"ZMQ PUSH 已连接到 {endpoint}")

    def send(self, message: dict) -> None:
        """将字典序列化为 JSON 并通过 ZMQ PUSH 发送。"""
        data = json.dumps(message, ensure_ascii=False).encode("utf-8")
        self._socket.send(data, flags=zmq.NOBLOCK)
        logger.debug(f"ZMQ 消息已发送: event={message.get('event')}, video_id={message.get('video_id')}")

    def send_task(self, task: Task) -> None:
        """将 Task 对象序列化为 JSON 并通过 ZMQ PUSH 发送。"""
        data = task.model_dump_json().encode("utf-8")
        self._socket.send(data, flags=zmq.NOBLOCK)
        logger.debug(f"ZMQ Task 已发送: type={task.task_type}, video_id={task.video_id}")

    def close(self) -> None:
        """关闭 socket 并终止 ZMQ 上下文。"""
        self._socket.close(linger=1000)
        self._context.term()
        logger.debug("ZMQ 连接已关闭")


class ZmqConsumer:
    """ZMQ PULL 消费者，绑定到 TCP 端点接收 Task 对象。"""

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint
        self._context = zmq.Context()
        self._socket = self._context.socket(zmq.PULL)
        self._socket.set_hwm(1000)
        self._socket.setsockopt(zmq.RCVTIMEO, 1000)
        self._socket.bind(endpoint)
        logger.info(f"ZMQ PULL 已绑定到 {endpoint}")

    def recv_task(self) -> Task:
        """阻塞接收一条消息并反序列化为 Task 对象。"""
        data = self._socket.recv()
        return Task.model_validate_json(data)

    def close(self) -> None:
        """关闭 socket 并终止 ZMQ 上下文。"""
        self._socket.close(linger=1000)
        self._context.term()
        logger.info("ZMQ PULL 连接已关闭")
