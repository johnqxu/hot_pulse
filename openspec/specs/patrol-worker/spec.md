## ADDED Requirements

### Requirement: 巡检 Worker 定时扫描

系统 SHALL 提供巡检 Worker，按配置的间隔（默认 60 分钟）定时扫描飞书表格，检测需要恢复的任务。

#### Scenario: 定时触发巡检
- **WHEN** 距上次巡检已过 interval_minutes 分钟
- **THEN** 系统 SHALL 执行一轮巡检扫描

#### Scenario: 巡检扫描执行
- **WHEN** 巡检触发
- **THEN** 系统 SHALL 对每种 running_status 和 fail_status 分别查询飞书表格
- **AND** 对查询到的记录逐条判断是否需要回退

### Requirement: 僵尸任务检测与恢复

系统 SHALL 检测停滞超过阈值的 running 状态任务。阈值由 `zombie_threshold_minutes` 配置（默认 90 分钟）。检测到僵尸任务时，系统 SHALL 将飞书状态回退到该阶段的 init_status，并通过 ZMQ PUSH 通知对应 worker（当前临时实现，计划改为直接调用 pipeline）。

#### Scenario: 发现僵尸任务
- **WHEN** 巡检发现某条记录的 running_status 对应的 start_field 时间距今超过 zombie_threshold_minutes
- **THEN** 系统 SHALL 将该记录的飞书"状态"字段更新为该阶段的 init_status
- **AND** 构造 Task 对象，通过 ZMQ PUSH 发送到对应 worker 的 pull_endpoint（当前实现）
- **AND** 后续 change 计划改为 `pipeline.run_subscription_pipeline(task, config, start_stage)`

#### Scenario: running 但未超时
- **WHEN** 巡检发现某条记录处于 running_status，但 start_field 时间距今未超过阈值
- **THEN** 系统 SHALL 跳过该记录，不做处理

### Requirement: 失败任务恢复

系统 SHALL 检测所有 fail_status 的记录，将飞书状态回退到该阶段的 init_status，并通过 ZMQ PUSH 通知对应 worker 重新处理（当前临时实现，计划改为直接调用 pipeline）。

#### Scenario: 发现失败任务
- **WHEN** 巡检发现某条记录的"状态"字段为某个阶段的 fail_status
- **THEN** 系统 SHALL 将该记录的飞书"状态"字段更新为该阶段的 init_status
- **AND** 构造 Task 对象，通过 ZMQ PUSH 发送到对应 worker 的 pull_endpoint（当前实现）
- **AND** 后续 change 计划改为 `pipeline.run_subscription_pipeline(task, config, start_stage)`

### Requirement: ZMQ 多端口路由（临时，计划废弃）

系统 SHALL 根据 task_type 将恢复的 Task 路由到对应 worker 的 pull_endpoint。路由映射从 STAGE_MAPPING 和 worker 配置中自动获取。此方案为 pipeline-executor 改动后的临时残留，计划在后续 change 中改为直接调用 pipeline 函数，彻底移除 ZMQ 依赖。

#### Scenario: 正确路由到 download worker
- **WHEN** 巡检恢复一个 download 阶段的任务
- **THEN** 系统 SHALL 将 Task 发送到 download worker 的 pull_endpoint（5551）

#### Scenario: ZMQ 发送失败
- **WHEN** ZMQ PUSH 发送失败
- **THEN** 系统 SHALL 记录警告日志但不阻塞后续任务处理
- **AND** 依赖 worker 启动恢复机制兜底（下次重启时从飞书查询 init_status）

### Requirement: 独立运行

巡检 Worker SHALL 作为独立进程运行，通过 `python -m hot_pulse.patrol_worker` 启动。main.py 不再管理子进程（pipeline-executor 改动后已改为单进程）。

#### Scenario: 独立运行巡检
- **WHEN** 执行 `python -m hot_pulse.patrol_worker`
- **THEN** 巡检 Worker SHALL 独立启动并运行定时循环，不依赖 main.py

#### Scenario: 与 main.py 的关系
- **WHEN** 系统部署
- **THEN** patrol_worker 和 main.py SHALL 作为两个独立进程分别启动
- **AND** main.py 负责 monitor 定时调度，patrol_worker 负责僵尸/失败任务恢复
