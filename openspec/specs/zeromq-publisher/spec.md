## Purpose

ZMQ 基础设施（已弃用）。ZmqPublisher 和 ZmqConsumer 类已随 pipeline-executor 改动移除。仅 patrol_worker 内部仍使用 pyzmq 进行恢复任务的临时路由（计划后续迁移到 pipeline 直接调用）。

## Requirements

### Requirement: ZMQ 已废弃

ZmqPublisher（ZMQ PUSH 客户端）和 ZmqConsumer（ZMQ PULL 消费者）类已从代码库中删除。monitor.py 和 ingest.py 不再通过 ZMQ 发送 Task，改为直接调用 `pipeline.run_subscription_pipeline()` 和 `pipeline.run_manual_pipeline()`。

#### Scenario: monitor/ingest 不使用 ZMQ
- **WHEN** monitor 发现新视频或 ingest 提交新内容
- **THEN** 系统 SHALL 直接函数调用 pipeline，不经过 ZMQ PUSH

#### Scenario: worker 不再常驻监听 ZMQ
- **WHEN** 系统处理任务
- **THEN** worker handler 由 pipeline._run_stages() 直接调用，不经过 ZMQ PULL 接收

### Requirement: patrol_worker 临时 ZMQ 路由

patrol_worker 内部仍使用 pyzmq 创建 PUSH socket，将恢复的 Task 路由到各 task_type 对应的端点。此用法为临时方案，计划在后续 change 中改为直接调用 `pipeline.run_subscription_pipeline(task, config, start_stage)`。

#### Scenario: patrol ZMQ 路由（临时）
- **WHEN** patrol_worker 检测到需要恢复的任务
- **THEN** 系统 SHALL 通过 ZMQ PUSH 发送 Task（当前实现）
- **AND** 后续 change 将改为直接调用 pipeline 函数

### Requirement: 按状态查询飞书记录

系统 SHALL 提供 FeishuClient 方法，按飞书表格"状态"字段查询记录，返回 Task 对象列表。此功能由 pipeline.recover_interrupted_tasks() 和 patrol_worker 共同使用。

#### Scenario: 查询到匹配记录
- **WHEN** 调用 query_records_by_status(status, task_type)
- **THEN** 系统 SHALL 查询飞书表格中"状态"字段等于指定值的所有记录
- **AND** 将每条记录构造为 Task 对象，task_type 为指定值
- **AND** 从记录中提取 video_id、creator、title、feishu_record_id 和阶段对应的 inputs

#### Scenario: 无匹配记录
- **WHEN** 指定状态在飞书表格中无匹配记录
- **THEN** 系统 SHALL 返回空列表
