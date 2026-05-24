## 1. pipeline.py 实现 (TDD)

- [x] 1.1 测试: `run_subscription_pipeline` 存在且可调用
- [x] 1.2 测试: subscription 管道按顺序调用 5 个 handler
- [x] 1.3 测试: 阶段失败时 pipeline 停止，不执行后续
- [x] 1.4 测试: manual 管道调用 knowledge handler

## 2. monitor.py / ingest.py 集成

- [x] 2.1 monitor.py 去掉 ZMQ，调用 `run_subscription_pipeline`
- [x] 2.2 ingest.py 去掉 ZMQ，调用 `run_manual_pipeline`

## 3. 验证

- [x] 3.1 pytest 4/4 通过
- [x] 3.2 编译验证通过
