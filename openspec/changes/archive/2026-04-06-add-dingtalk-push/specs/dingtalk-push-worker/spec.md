## ADDED Requirements

### Requirement: 钉钉消息推送 handler
系统 SHALL 提供 `handle_dingtalk_push(task, config)` handler 函数，读取报告文件并通过钉钉 Webhook 推送到群聊，作为流水线终端阶段。

#### Scenario: 成功推送报告
- **WHEN** task.inputs 包含有效的 report_file 路径
- **AND** 报告文件存在且可读
- **THEN** 系统 SHALL 读取报告全文
- **AND** 构造钉钉 Markdown 消息（title=视频标题，text=报告全文）
- **AND** 使用加签方式调用 Webhook API
- **AND** 返回 `{"push_status": "ok"}`

#### Scenario: 报告文件不存在
- **WHEN** task.inputs 中的 report_file 路径对应的文件不存在
- **THEN** 系统 SHALL 抛出 RuntimeError 说明文件不存在

#### Scenario: task.inputs 缺少 report_file
- **WHEN** task.inputs 中没有 report_file 键
- **THEN** 系统 SHALL 抛出 RuntimeError 说明缺少必要输入

### Requirement: 钉钉 Webhook 加签认证
系统 SHALL 使用 HMAC-SHA256 加签方式构造 Webhook 请求 URL，确保消息安全性。

#### Scenario: 构造加签 URL
- **WHEN** 发送钉钉消息时
- **THEN** 系统 SHALL 使用当前毫秒时间戳和 Secret 计算 HMAC-SHA256 签名
- **AND** 将 timestamp 和 sign 参数附加到 Webhook URL
- **AND** 使用 POST 方法发送 JSON 请求体

#### Scenario: Secret 未配置
- **WHEN** .env 中未配置 DINGTALK_SECRET 或 config 中未配置 webhook_url
- **THEN** 系统 SHALL 抛出 RuntimeError 说明配置缺失

### Requirement: 流控机制
系统 SHALL 实现消息发送间隔控制，确保连续两条消息之间至少间隔 2 分钟（120 秒）。

#### Scenario: 首次发送
- **WHEN** worker 启动后首次发送消息
- **THEN** 系统 SHALL 立即发送，无需等待

#### Scenario: 发送间隔不足 2 分钟
- **WHEN** 距上次成功发送不足 120 秒
- **THEN** 系统 SHALL sleep 等待至 120 秒后再发送

#### Scenario: 发送间隔超过 2 分钟
- **WHEN** 距上次成功发送已超过 120 秒
- **THEN** 系统 SHALL 立即发送，无需等待

### Requirement: 钉钉 API 响应处理
系统 SHALL 检查钉钉 Webhook API 的响应状态，处理成功和失败情况。

#### Scenario: Webhook 返回成功
- **WHEN** 钉钉 API 返回 HTTP 200 且 errcode 为 0
- **THEN** 系统 SHALL 记录日志并正常返回

#### Scenario: Webhook 返回错误
- **WHEN** 钉钉 API 返回非 200 状态码或 errcode 不为 0
- **THEN** 系统 SHALL 抛出 RuntimeError 包含错误码和错误信息

#### Scenario: 网络请求超时
- **WHEN** Webhook 请求超过 30 秒未响应
- **THEN** 系统 SHALL 抛出超时异常

### Requirement: dingtalk_push worker CLI 入口
系统 SHALL 提供独立的 CLI 入口点，支持直接运行 `python -m hot_pulse.dingtalk_worker`。

#### Scenario: 直接运行 worker
- **WHEN** 执行 `python -m hot_pulse.dingtalk_worker`
- **THEN** 系统 SHALL 配置 loguru 日志输出到 stderr
- **AND** 调用 `run_worker("dingtalk_push", handle_dingtalk_push)`

### Requirement: 钉钉消息格式
系统 SHALL 构造符合钉钉 Webhook API 的 Markdown 消息格式。

#### Scenario: 消息结构
- **WHEN** 构造钉钉消息
- **THEN** 消息体 SHALL 为 JSON 格式：`{"msgtype": "markdown", "markdown": {"title": "<视频标题>", "text": "<报告全文>"}}`
- **AND** Content-Type SHALL 为 `application/json`
