## Why

监控模块当前发现新视频后仅写入飞书表格，后续阶段（下载、提取音频、转写、分析）无法实时感知新任务到来。需要引入消息通知机制，使下游常驻进程能立即收到新任务通知，无需轮询飞书表格。

选用 ZeroMQ（pyzmq）作为消息传输层：
- Brokerless，无需额外服务进程
- 支持跨进程 tcp:// 通信
- PUSH/PULL 模式天然适配流水线
- Python 客户端 pyzmq 成熟稳定

## What Changes

- 新增 `zmq_client.py` 模块，封装 ZMQ PUSH 客户端（连接 + 发送）
- 修改 `monitor.py`，在飞书写入成功后调用 ZMQ 客户端发送任务消息
- 修改 `config.py`，新增 ZMQ 端点配置模型
- 修改 `config.yaml`，新增 zeromq 配置段
- 新增依赖 pyzmq

## Capabilities

### New Capabilities
- `zeromq-publisher`: ZMQ PUSH 消息发送能力，将新视频任务以 JSON 格式推送到指定端点

### Modified Capabilities
- `douyin-monitor`: 监控发现新视频后，除写入飞书表格外，还需发送 ZMQ 消息通知下游

## Impact

- 新增依赖：pyzmq
- 飞书表格作为持久化真相来源不变，ZMQ 仅作为实时通知加速器
- ZMQ 连接失败不阻塞监控主流程
