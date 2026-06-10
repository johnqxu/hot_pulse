## MODIFIED Requirements

### Requirement: 僵尸任务检测与恢复

系统 SHALL 检测停滞超过阈值的 running 状态任务。阈值由 `zombie_threshold_minutes` 配置（默认 90 分钟）。检测到僵尸任务时，系统 SHALL 将飞书状态回退到该阶段的 init_status，并直接调用 `pipeline.run_subscription_pipeline(task, config, start_stage)` 或 `pipeline.run_manual_pipeline(task, config, start_stage)` 从对应阶段恢复执行。

#### Scenario: 发现僵尸任务
- **WHEN** 巡检发现某条记录的 running_status 对应的 start_field 时间距今超过 zombie_threshold_minutes
- **THEN** 系统 SHALL 将该记录的飞书"状态"字段更新为该阶段的 init_status
- **AND** 构造 Task 对象，根据 Task.source 调用 `pipeline.run_subscription_pipeline(task, config, start_stage)`（subscription 来源）或 `pipeline.run_manual_pipeline(task, config, start_stage)`（manual 来源）
- **AND** 不再使用 ZMQ PUSH 发送任务

#### Scenario: running 但未超时
- **WHEN** 巡检发现某条记录处于 running_status，但 start_field 时间距今未超过阈值
- **THEN** 系统 SHALL 跳过该记录，不做处理

### Requirement: 失败任务恢复

系统 SHALL 检测所有 fail_status 的记录，将飞书状态回退到该阶段的 init_status，并直接调用 pipeline 函数从对应阶段重新执行。

#### Scenario: 发现失败任务
- **WHEN** 巡检发现某条记录的"状态"字段为某个阶段的 fail_status
- **THEN** 系统 SHALL 将该记录的飞书"状态"字段更新为该阶段的 init_status
- **AND** 构造 Task 对象，根据 Task.source 调用对应的 pipeline 函数恢复执行
- **AND** 不再使用 ZMQ PUSH 发送任务

## REMOVED Requirements

### Requirement: ZMQ 多端口路由（临时，计划废弃）

**Reason**: pipeline-executor 改动后，系统已统一使用 `pipeline.run_subscription_pipeline()` 和 `pipeline.run_manual_pipeline()` 直接函数调用执行管道，不再需要 ZMQ 多进程路由。

**Migration**: patrol_worker 恢复任务时直接调用 `pipeline.run_*_pipeline(task, config, start_stage)`，无需额外迁移步骤。已有的 ZMQ worker 进程（如果仍在运行）应手动停止。
