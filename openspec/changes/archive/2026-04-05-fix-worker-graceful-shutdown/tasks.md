## 1. ZmqConsumer 超时

- [x] 1.1 修改 `src/hot_pulse/zmq_client.py`：ZmqConsumer 初始化时设置 `RCVTIMEO=1000`，recv_task() 超时时抛出 zmq.Again

## 2. Worker 主循环

- [x] 2.1 修改 `src/hot_pulse/worker_base.py`：主循环捕获 zmq.Again 超时，检查 shutting_down 后继续循环或退出

## 3. 验证

- [x] 3.1 启动 worker，按 Ctrl+C 验证 1 秒内优雅退出
