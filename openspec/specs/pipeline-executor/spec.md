## Purpose

单进程串行管道编排器，替代 ZMQ 多进程架构。monitor/ingest 直接函数调用串联 worker handler 函数，支持从中间阶段恢复和启动恢复。同时定义 WorkerHandler 协议和日志规范。

## Requirements

### Requirement: WorkerHandler 协议

系统 SHALL 定义 WorkerHandler 类型协议，签名为 `(Task, AppConfig) -> dict`。每个具体 worker 模块（`*_worker.py`）提供一个符合此签名的 handler 函数，由 `pipeline._run_stages()` 直接调用。

#### Scenario: handler 返回 outputs dict
- **WHEN** handler 成功执行完毕
- **THEN** handler SHALL 返回 dict 类型的 outputs，包含当前阶段的产出物
- **AND** TaskManager 将 outputs 写入飞书记录，并用于构建下一阶段 Task

#### Scenario: handler 抛出异常表示失败
- **WHEN** handler 执行过程中遇到错误
- **THEN** handler SHALL 抛出异常，异常消息作为任务失败原因
- **AND** pipeline SHALL 调用 `TaskManager.fail()` 标记失败并停止后续阶段

### Requirement: 串行管道执行

系统 SHALL 提供 `run_subscription_pipeline` 和 `run_manual_pipeline` 函数，按顺序串行调用 worker handler。每个阶段通过 TaskManager 管理生命周期（start → handler → finish → build_next）。

#### Scenario: subscription 管道
- **WHEN** 调用 `run_subscription_pipeline(task, config)`
- **THEN** 系统 SHALL 顺序执行 download → extract_audio → transcribe → analyze → dingtalk_push

#### Scenario: manual 管道
- **WHEN** 调用 `run_manual_pipeline(task, config)`
- **THEN** 系统 SHALL 顺序执行 download → extract_audio → transcribe → knowledge

#### Scenario: 成功处理单个阶段
- **WHEN** pipeline 执行某个阶段
- **THEN** 系统 SHALL 调用 `tm.start(task)` 更新飞书状态为 running_status
- **AND** 调用 `handler(task, config)` 执行业务逻辑
- **AND** 调用 `tm.finish(task, outputs)` 更新飞书状态为 finish_status
- **AND** 调用 `tm.build_next(task)` 构建下一阶段 Task

### Requirement: 阶段失败停止

系统 SHALL 在某个阶段失败时停止执行后续阶段，调用 TaskManager.fail 标记失败状态。

#### Scenario: handler 抛出异常
- **WHEN** handler 执行过程中抛出异常
- **THEN** pipeline SHALL 调用 `tm.fail(task, error_message)`
- **AND** 不再执行后续阶段

#### Scenario: 最后一个阶段
- **WHEN** tm.build_next(task) 返回 None（无下一阶段）
- **THEN** pipeline SHALL 停止执行

### Requirement: 从中间阶段恢复

系统 SHALL 支持 `start_stage` 参数，跳过前面的阶段，从指定阶段开始执行。

### Requirement: 启动恢复

系统 SHALL 提供 `recover_interrupted_tasks` 函数，启动时从飞书查询非终端状态任务并恢复执行。

#### Scenario: 有中断任务
- **WHEN** 飞书表格中存在非终端状态记录（新视频、视频下载中、音频提取中、文字转写中、报告分析中、报告推送中、知识整理中）
- **THEN** 系统 SHALL 逐条恢复，根据飞书状态映射到对应 pipeline stage，从该 stage 继续执行

#### Scenario: 无中断任务
- **WHEN** 飞书表格中无非终端状态记录
- **THEN** 系统 SHALL 记录日志并跳过

### Requirement: Worker 日志标识

各 handler 模块 SHALL 使用带颜色的进程标识前缀输出日志。不同 task_type 对应不同颜色：download=青色、extract_audio=黄色、transcribe=蓝色、analyze=洋红、dingtalk_push=红色、knowledge=灰色、patrol=浅黑。

#### Scenario: Handler 执行日志
- **WHEN** pipeline 调用 handler 执行
- **THEN** 日志格式为 `{time} | {level} | <color>[task_type]</color> {message}`，颜色按 task_type 映射

#### Scenario: 独立运行
- **WHEN** 通过 `python -m hot_pulse.monitor` 或其他模块独立启动
- **THEN** 日志同样使用对应颜色的前缀
