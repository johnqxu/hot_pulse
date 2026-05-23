## Why

Transcribe 完成后 `next_type` 固定指向 `analyze`（财经分析），所有任务不分来源都走同一路径。需要根据 `Task.source` 分流：subscription → analyze → dingtalk，manual → knowledge → Obsidian。

## What Changes

- `STAGE_MAPPING` 新增 `knowledge` 阶段配置
- `TaskManager.build_next` 在 transcribe 阶段根据 `task.source` 选择 `next_type`（`"manual"` → `"knowledge"`, 默认 → `"analyze"`）

## Capabilities

### New Capabilities

- `transcribe-source-route`: Transcribe 完成后根据 Task.source 分流到不同后续阶段

### Modified Capabilities

- `task-model`: STAGE_MAPPING 新增 knowledge 阶段

## Impact

- **代码**: `task_manager.py` 只改 `build_next` 方法（约 5 行）和 `STAGE_MAPPING`（约 10 行）
- **管道**: 不影响现有 subscription 路径，manual 路径新增 knowledge 阶段
