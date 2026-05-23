## Purpose

Transcribe 完成后根据 Task.source 分流到不同后续阶段：subscription → analyze（财经分析），manual → knowledge（知识整理）。

## Requirements

### Requirement: build_next 按 source 分流

系统 SHALL 在 transcribe 阶段完成后根据 `task.source` 值选择下一阶段。

#### Scenario: subscription 进入 analyze
- **WHEN** transcribe 完成且 `task.source="subscription"`
- **THEN** `build_next` SHALL 返回 `task_type="analyze"` 的 Task

#### Scenario: manual 进入 knowledge
- **WHEN** transcribe 完成且 `task.source="manual"`
- **THEN** `build_next` SHALL 返回 `task_type="knowledge"` 的 Task

#### Scenario: source 透传
- **WHEN** `build_next` 构造下一阶段 Task
- **THEN** 新 Task 的 `source` SHALL 继承自当前 Task

### Requirement: knowledge 阶段配置

系统 SHALL 在 STAGE_MAPPING 中提供 `knowledge` 阶段配置。

#### Scenario: knowledge 阶段状态
- **WHEN** knowledge 阶段启动
- **THEN** 飞书状态 SHALL 更新为 `知识整理中`
- **AND** 完成时更新为 `知识整理完成`
- **AND** 失败时更新为 `知识整理失败`
- **AND** `next_type` 为 None（当前为终端阶段）
