## MODIFIED Requirements

### Requirement: 将新视频记录写入飞书多维表格
系统 SHALL 将每条新视频作为一条新记录写入飞书多维表格，按照字段映射填充字段。

#### Scenario: 写入单条新视频记录
- **WHEN** 检测到某个创作者有新视频
- **THEN** 系统 SHALL 按照字段映射创建包含所有字段的记录
- **AND** 飞书写入成功后，系统 SHALL 捕获飞书返回的 record_id
- **AND** 系统 SHALL 构造 Task 对象（task_type="download"，feishu_record_id=record_id，inputs 包含 play_urls）
- **AND** 通过 ZMQ PUSH 发送 Task

#### Scenario: 飞书 API 写入失败
- **WHEN** 写入飞书多维表格失败
- **THEN** 系统 SHALL 记录错误日志，且不为该记录发送 ZMQ 消息
- **AND** 继续处理剩余新视频

#### Scenario: ZMQ 发送失败
- **WHEN** 发送 ZMQ 消息失败（连接错误、超时）
- **THEN** 系统 SHALL 记录错误日志但不阻塞监控工作流
- **AND** 继续处理剩余新视频
