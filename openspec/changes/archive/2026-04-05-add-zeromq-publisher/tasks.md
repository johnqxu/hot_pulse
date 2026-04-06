## 1. 配置扩展

- [x] 1.1 修改 `src/hot_pulse/config.py`：新增 `ZeroMQConfig` 模型（`enabled: bool`, `push_endpoint: str`），在 `AppConfig` 中新增 `zeromq` 字段
- [x] 1.2 修改 `config.yaml`：新增 `zeromq` 配置段（`enabled: true`, `push_endpoint: "tcp://127.0.0.1:5551"`）

## 2. ZMQ 客户端

- [x] 2.1 新增 `src/hot_pulse/zmq_client.py`：实现 ZmqPublisher 类，包含 PUSH socket 创建、connect、send_json（自动序列化 dict 为 JSON）、close 方法

## 3. 监控集成

- [x] 3.1 修改 `src/hot_pulse/monitor.py`：在 `_process_creator` 中飞书写入成功后，调用 ZmqPublisher.send() 发送任务消息；ZMQ 操作失败时记录错误日志但不阻塞主流程

## 4. 依赖与验证

- [x] 4.1 修改 `pyproject.toml`：新增 `pyzmq>=25.0` 依赖
- [x] 4.2 安装依赖并运行 `python -m hot_pulse.monitor`，确认 ZMQ 消息发送正常（可配合简单 PULL 测试脚本验证）
