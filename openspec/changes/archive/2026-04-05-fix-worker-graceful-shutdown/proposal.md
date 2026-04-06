## Why

Worker 的 `run_worker()` 主循环中，`consumer.recv_task()` 调用 ZMQ 阻塞式 `socket.recv()`。在 Windows 上，Python 信号处理器无法中断 C 层的阻塞调用，导致 Ctrl+C 无法触发优雅关闭，进程卡死。

## What Changes

- 修改 `src/hot_pulse/zmq_client.py`：ZmqConsumer 的 `recv_task()` 设置 `RCVTIMEO` 超时（1 秒），超时时抛出 `zmq.Again` 异常
- 修改 `src/hot_pulse/worker_base.py`：主循环捕获 `zmq.Again`，检查 `shutting_down` 标志后继续或退出

## Capabilities

### New Capabilities

（无）

### Modified Capabilities
- `zeromq-publisher`: ZmqConsumer.recv_task() 改为带超时的非阻塞模式，超时时抛出 zmq.Again
- `worker-base`: run_worker 主循环处理 zmq.Again 超时，实现 Windows 下的优雅关闭

## Impact

- 修改文件：`src/hot_pulse/zmq_client.py`、`src/hot_pulse/worker_base.py`
- recv_task() 的调用方需处理 zmq.Again（仅 worker_base.py）
