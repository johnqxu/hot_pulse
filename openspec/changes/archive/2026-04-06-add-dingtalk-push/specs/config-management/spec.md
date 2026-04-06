## ADDED Requirements

### Requirement: DingTalkWorkerConfig 配置模型
系统 SHALL 提供 DingTalkWorkerConfig 继承 WorkerConfig，包含 webhook_url 和 min_interval 配置。

#### Scenario: dingtalk_worker 配置
- **WHEN** config.yaml 中配置了 dingtalk_worker
- **THEN** 系统 SHALL 将其解析为 DingTalkWorkerConfig，包含 pull_endpoint、push_endpoint、webhook_url 和 min_interval

#### Scenario: min_interval 缺省
- **WHEN** config.yaml 中未配置 dingtalk_worker.min_interval
- **THEN** min_interval SHALL 默认为 120（秒）

#### Scenario: AppConfig 包含 dingtalk_worker
- **WHEN** 系统加载配置
- **THEN** AppConfig SHALL 包含 dingtalk_worker 字段，类型为 DingTalkWorkerConfig，提供默认值

### Requirement: DINGTALK_SECRET 环境变量
系统 SHALL 从 .env 文件加载 DINGTALK_SECRET，用于钉钉 Webhook 加签认证。

#### Scenario: 成功加载 DINGTALK_SECRET
- **WHEN** .env 文件包含有效的 DINGTALK_SECRET
- **THEN** 系统 SHALL 将其用于 HMAC-SHA256 加签计算

#### Scenario: 缺少 DINGTALK_SECRET
- **WHEN** .env 文件中未配置 DINGTALK_SECRET
- **THEN** 系统 SHALL 允许启动，仅在 dingtalk_push worker 实际调用 Webhook 时才抛出错误
