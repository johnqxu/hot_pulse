## Purpose

ZMQ PUSH/PULL 客户端，支持 Task 对象的发送和接收。

## Requirements

### Requirement: ZMQ PUSH 客户端初始化
系统 SHALL 提供 ZMQ 发布者客户端，创建 PUSH socket 并连接到可配置的 TCP 端点，支持发送 Task 对象。

#### Scenario: 成功初始化
- **WHEN** 使用有效的端点（如 "tcp://127.0.0.1:5551"）创建 ZMQ 发布者客户端
- **THEN** 客户端 SHALL 创建 ZMQ PUSH socket 并连接到端点
- **AND** 调用 send_task(task) 时 SHALL 将 Task 序列化为 JSON 并通过 socket 发送

#### Scenario: 客户端关闭
- **WHEN** 调用客户端的 close() 方法
- **THEN** 客户端 SHALL 关闭 socket 并终止 ZMQ 上下文

### Requirement: ZMQ PULL 消费者
系统 SHALL 提供 ZMQ 消费者客户端，创建 PULL socket 并绑定到 TCP 端点，支持接收 Task 对象，socket 设置 1 秒接收超时。

#### Scenario: 成功接收 Task
- **WHEN** ZMQ PULL socket 收到 JSON 消息
- **THEN** 系统 SHALL 通过 `Task.model_validate_json()` 反序列化为 Task 对象并返回

#### Scenario: 接收超时
- **WHEN** ZMQ PULL socket 在 RCVTIMEO（1 秒）内未收到消息
- **THEN** recv_task() SHALL 抛出 `zmq.Again` 异常

#### Scenario: 消费者关闭
- **WHEN** 调用消费者的 close() 方法
- **THEN** 消费者 SHALL 关闭 socket 并终止 ZMQ 上下文

### Requirement: 按状态查询飞书记录
系统 SHALL 提供 FeishuClient 方法，按飞书表格"状态"字段查询记录，返回 Task 对象列表。

#### Scenario: 查询到匹配记录
- **WHEN** 调用 query_records_by_status(status, task_type)
- **THEN** 系统 SHALL 查询飞书表格中"状态"字段等于指定值的所有记录
- **AND** 将每条记录构造为 Task 对象，task_type 为指定值
- **AND** 从记录中提取 video_id、creator、title、feishu_record_id 和阶段对应的 inputs

#### Scenario: 无匹配记录
- **WHEN** 指定状态在飞书表格中无匹配记录
- **THEN** 系统 SHALL 返回空列表
