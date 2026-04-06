## Why

Worker 启动时直接进入 ZMQ recv 主循环，不从飞书读取历史任务。如果 worker 崩溃重启，或者 monitor 和 worker 之间 ZMQ 消息丢失，飞书中状态为"新视频"的记录永远不会被处理。飞书是唯一的持久化真相来源，worker 应该在启动时从中恢复未完成的任务。

## What Changes

- 修改 `src/hot_pulse/task_manager.py`：StageConfig 新增 `init_status` 和 `finish_status` 字段；TaskManager.finish() 写入 finish_status 到飞书"状态"字段
- 修改 `src/hot_pulse/feishu.py`：新增 `query_records_by_status(status)` 方法，查询指定状态的所有记录并返回 Task 列表
- 修改 `src/hot_pulse/worker_base.py`：run_worker() 启动时调用飞书查询 init_status 对应的记录，逐条构造 Task 交给 handler 处理，处理完成后再进入 ZMQ 主循环
- 飞书表格新增单选值："视频下载完成"、"音频提取完成"、"文字转写完成"、"分析完成"

## Capabilities

### New Capabilities

（无）

### Modified Capabilities
- `task-model`: StageConfig 新增 init_status 和 finish_status 字段，定义四个阶段的状态映射
- `worker-base`: run_worker() 启动时从飞书加载 init_status 对应的历史任务，处理完后再进入 ZMQ 主循环
- `download-worker`: 不变（由 worker-base 和 task-model 的变更自动覆盖）
- `zeromq-publisher`: FeishuClient 新增 query_records_by_status 方法

## Impact

- 修改文件：`task_manager.py`、`feishu.py`、`worker_base.py`
- 飞书表格：新增 4 个单选值
- 无新文件、无新依赖
