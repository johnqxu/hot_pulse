## MODIFIED Requirements

### Requirement: 将新视频记录写入飞书多维表格
系统 SHALL 将每条新视频作为一条新记录写入飞书多维表格，按照字段映射填充字段。

#### Scenario: 写入单条新视频记录
- **WHEN** 检测到某个创作者有新视频
- **THEN** 系统 SHALL 按照字段映射创建包含所有字段的记录
- **AND** 飞书写入成功后，系统 SHALL 通过 ZMQ PUSH 向配置的端点发送包含任务详情的消息

#### Scenario: 飞书 API 写入失败
- **WHEN** 写入飞书多维表格失败
- **THEN** 系统 SHALL 记录错误日志，且不为该记录发送 ZMQ 消息
- **AND** 继续处理剩余新视频

#### Scenario: ZMQ 发送失败
- **WHEN** 发送 ZMQ 消息失败（连接错误、超时）
- **THEN** 系统 SHALL 记录错误日志但不阻塞监控工作流
- **AND** 继续处理剩余新视频

## ADDED Requirements

### Requirement: ZMQ PUSH 消息格式
系统 SHALL 通过 ZMQ PUSH socket 发送以任务为中心结构的 JSON 消息。

#### Scenario: 消息结构
- **WHEN** 发现新视频并写入飞书
- **THEN** ZMQ 消息 SHALL 包含：task_id、event（"new_video"）、stage（"download"）、video_id、creator、title、play_urls、feishu_record_id、discovered_at

### Requirement: ZMQ 配置
系统 SHALL 从 config.yaml 加载 ZMQ 配置，包括端点地址和启用标志。

#### Scenario: ZMQ 已禁用
- **WHEN** config.yaml 中 zeromq.enabled 设置为 false
- **THEN** 系统 SHALL 跳过所有 ZMQ 操作，仅写入飞书

#### Scenario: ZMQ 配置缺失
- **WHEN** config.yaml 不包含 zeromq 配置段
- **THEN** 系统 SHALL 默认禁用 ZMQ，记录警告日志，以仅飞书模式继续运行
