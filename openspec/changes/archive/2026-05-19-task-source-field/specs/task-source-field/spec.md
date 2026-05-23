## Purpose

Task 模型支持 `source` 字段，标识视频任务来源（`"subscription"` = TikTok 定时监控，`"manual"` = 用户手动提交），为后续按来源分流提供基础。

## ADDED Requirements

### Requirement: Task.source 字段

系统 SHALL 在 Task 模型中提供 `source` 字段，标识视频任务的来源类型。

#### Scenario: source 默认值
- **WHEN** 构造 Task 对象时未显式传入 `source`
- **THEN** source SHALL 默认为 `"subscription"`

#### Scenario: source 值为 subscription
- **WHEN** monitor 通过 TikTok 轮询发现新视频
- **THEN** 构造的 Task SHALL 带有 `source="subscription"`

#### Scenario: source 值为 manual
- **WHEN** 用户通过 OpenClaw Skill / CLI 手动提交视频
- **THEN** 构造的 Task SHALL 带有 `source="manual"`

#### Scenario: ZMQ 序列化兼容
- **WHEN** Task 对象通过 ZMQ 序列化为 JSON
- **THEN** source 字段 SHALL 自动包含在 JSON 中
- **AND** 下游 worker 反序列化后 SHALL 可读取 source 值

#### Scenario: 向后兼容
- **WHEN** 现有代码构造 Task 对象（monitor 之外）
- **THEN** 系统 SHALL 无需任何代码修改，默认 source="subscription" 保证行为不变
