## Purpose

单进程串行管道编排器，替代 ZMQ 多进程架构。monitor/ingest 直接函数调用串联 worker handler 函数，支持从中间阶段恢复。

## Requirements

### Requirement: 串行管道执行
系统 SHALL 提供 `run_subscription_pipeline` 和 `run_manual_pipeline` 函数，按顺序串行调用 worker handler。

#### Scenario: subscription 管道
- **WHEN** 调用 `run_subscription_pipeline(task, config)`
- **THEN** 系统 SHALL 顺序执行 download → extract_audio → transcribe → analyze → dingtalk_push

#### Scenario: manual 管道
- **WHEN** 调用 `run_manual_pipeline(task, config)`
- **THEN** 系统 SHALL 顺序执行 download → extract_audio → transcribe → knowledge

### Requirement: 阶段失败停止
系统 SHALL 在某个阶段失败时停止执行后续阶段，调用 TaskManager.fail 标记失败状态。

### Requirement: 从中间阶段恢复
系统 SHALL 支持 `start_stage` 参数，跳过前面的阶段，从指定阶段开始执行。

### Requirement: 启动恢复
系统 SHALL 提供 `recover_interrupted_tasks` 函数，启动时从飞书查询非终端状态任务并恢复执行。
