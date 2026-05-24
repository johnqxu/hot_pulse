## Why

当前 7 个常驻 ZMQ worker 进程架构臃肿。需改为单进程串行管道：monitor/ingest 直接函数调用 pipeline，不再经过 ZMQ。简化架构，减少进程数和依赖。

## What Changes

- 新增 `pipeline.py` — 串行管道编排器，直接调用 worker handler 函数
- `monitor.py` — 去掉 ZMQ 推送，改为 `run_subscription_pipeline(task, config)`
- `ingest.py` — 去掉 ZMQ 推送，改为 `run_manual_pipeline(task, config)`
- ZMQ 基础设施暂时保留（Proposal 3 删除）
