## Why

当前 Task 模型无法区分视频来源——TikTok 定时监控（subscription）与用户手动提交（manual）的处理路径完全相同。后续需要根据来源分流到不同的下游分析管道（财经分析 vs 知识整理），需要先在 Task 模型上增加 `source` 字段作为分流标识。

## What Changes

- `Task` 模型新增 `source` 字段：`"subscription"`（默认，向后兼容）或 `"manual"`
- `monitor.py` 中 `_send_zmq_task` 显式传入 `source="subscription"`

## Capabilities

### New Capabilities

- `task-source-field`: Task 模型支持 `source` 字段，标识视频任务来源（subscription / manual）

### Modified Capabilities

（无）

## Impact

- **代码**: `task.py`（1 行新增）、`monitor.py`（1 行修改）
- **兼容性**: 完全向后兼容 — 默认值 `"subscription"` 保证所有已有调用无需修改
- **ZMQ**: pydantic 自动序列化，下游 worker 无需变动
- **worker_base / task_manager / 各 worker**: 无需改动
