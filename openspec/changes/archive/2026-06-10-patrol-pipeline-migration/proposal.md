## Why

patrol_worker 是系统内最后一个仍依赖 ZMQ 多进程架构的模块。pipeline-executor 改动后，monitor.py、ingest.py、main.py 均已改为直接调用 `pipeline.run_*_pipeline()` 函数，不再经过 ZMQ 路由。patrol_worker 内部仍通过 ZMQ PUSH socket 将恢复的 Task 推送到独立 worker 进程，与当前单进程串行管道架构不一致。Spec 中已明确标注此方案为"临时残留，计划在后续 change 中改为直接调用 pipeline 函数"。

## What Changes

- **移除 ZMQ 依赖**：删除 patrol_worker.py 中 `_build_push_routes()`、`_close_push_routes()`、`STAGE_REVERSE` 及所有 `zmq` 相关代码
- **直接调用 pipeline 函数**：巡检发现僵尸/失败任务后，根据任务来源（subscription/manual）调用 `pipeline.run_subscription_pipeline(task, config, start_stage)` 或 `pipeline.run_manual_pipeline(task, config, start_stage)`
- **复用现有设施**：使用 `pipeline._STATUS_TO_STAGE` 替代自建的 `STAGE_REVERSE` 反向映射；使用 `feishu.query_records_by_status()` 替代自建的 `_query_records_by_status()`
- **串行阻塞恢复**：采用方案 A——同步串行恢复每个僵尸/失败任务，不引入线程池或 asyncio
- **保持现有周期**：巡检间隔保持 60 分钟不变

## Capabilities

### New Capabilities

（无新增 capability，本次为架构对齐，不引入新功能）

### Modified Capabilities

- `patrol-worker`: 移除 ZMQ 多端口路由 requirement，改为直接调用 pipeline；巡检恢复逻辑从 ZMQ PUSH 改为同步函数调用

## Impact

- **patrol_worker.py**：主要变更文件，删除 ZMQ 相关代码（约 40 行），简化核心巡检逻辑
- **pipeline.py**：暴露 `STATUS_TO_STAGE` 映射供 patrol_worker 引用（或将 status→stage 查询逻辑下沉到 pipeline 模块）
- **pyproject.toml**：移除 `pyzmq` 依赖（如果其他模块不再使用）
- **不再有独立 worker 进程**：patrol 恢复的任务将直接在当前进程内串行执行 pipeline，不再依赖 download/transcribe 等 worker 进程
- **无 API 变更**：对外接口不变，`patrol_worker.main_loop()` 行为保持一致
