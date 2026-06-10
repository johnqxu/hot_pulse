## Purpose

Worker handler 函数协议与日志规范。worker 不再作为独立常驻进程运行；handler 函数由 `pipeline.py` 直接调用。`worker_base.py`（原 `run_worker()` 通用主循环）已删除。

## Requirements

### Requirement: WorkerHandler 协议

系统 SHALL 定义 WorkerHandler 类型协议，签名为 `(Task, AppConfig) -> dict`。每个具体 worker 模块提供一个符合此签名的 handler 函数，由 `pipeline._run_stages()` 直接调用。

#### Scenario: handler 返回 outputs dict
- **WHEN** handler 成功执行完毕
- **THEN** handler SHALL 返回 dict 类型的 outputs，包含当前阶段的产出物
- **AND** TaskManager 将 outputs 写入飞书记录，并用于构建下一阶段 Task

#### Scenario: handler 抛出异常表示失败
- **WHEN** handler 执行过程中遇到错误
- **THEN** handler SHALL 抛出异常，异常消息作为任务失败原因
- **AND** pipeline SHALL 调用 `TaskManager.fail()` 标记失败并停止后续阶段

### Requirement: Pipeline 编排调用

系统 SHALL 通过 `pipeline._run_stages()` 按阶段顺序调用 handler，管理 TaskManager 生命周期（start → handler → finish → build_next）。

#### Scenario: 成功处理单个阶段
- **WHEN** pipeline 执行某个阶段
- **THEN** 系统 SHALL 调用 `tm.start(task)` 更新飞书状态为 running_status
- **AND** 调用 `handler(task, config)` 执行业务逻辑
- **AND** 调用 `tm.finish(task, outputs)` 更新飞书状态为 finish_status
- **AND** 调用 `tm.build_next(task)` 构建下一阶段 Task

#### Scenario: 阶段失败停止
- **WHEN** handler 抛出异常
- **THEN** pipeline SHALL 调用 `tm.fail(task, error_message)`
- **AND** 不再执行后续阶段

#### Scenario: 最后一个阶段
- **WHEN** tm.build_next(task) 返回 None（无下一阶段）
- **THEN** pipeline SHALL 停止执行

### Requirement: Worker 日志标识

各 handler 模块 SHALL 使用带颜色的进程标识前缀输出日志。不同 task_type 对应不同颜色：download=青色、extract_audio=黄色、transcribe=蓝色、analyze=洋红、dingtalk_push=红色、knowledge=灰色、patrol=浅黑。

#### Scenario: Handler 执行日志
- **WHEN** pipeline 调用 handler 执行
- **THEN** 日志格式为 `{time} | {level} | <color>[task_type]</color> {message}`，颜色按 task_type 映射

#### Scenario: 独立运行
- **WHEN** 通过 `python -m hot_pulse.monitor` 或其他模块独立启动
- **THEN** 日志同样使用对应颜色的前缀
