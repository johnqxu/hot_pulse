## MODIFIED Requirements

### Requirement: SecretConfig 凭证管理

`SecretConfig` SHALL 从 `.env` 文件读取所有敏感凭证。新增字段：`feishu_bitable_app_token`、`feishu_bitable_table_id`、`dingtalk_webhook_url`。

#### Scenario: 从 .env 读取飞书 bitable 凭证
- **WHEN** `.env` 中配置了 `FEISHU_BITABLE_APP_TOKEN` 和 `FEISHU_BITABLE_TABLE_ID`
- **THEN** `SecretConfig` SHALL 正确解析这两个值

#### Scenario: 从 .env 读取钉钉 webhook
- **WHEN** `.env` 中配置了 `DINGTALK_WEBHOOK_URL`
- **THEN** `SecretConfig` SHALL 正确解析该值

### Requirement: load_config 凭证合并

`load_config()` SHALL 将 `SecretConfig` 中的敏感凭证注入到对应的配置模型中，优先使用环境变量值。当环境变量为空时，SHALL 回退到 `config.yaml` 中的值。

#### Scenario: 环境变量覆盖 YAML 值
- **WHEN** `.env` 中有 `FEISHU_BITABLE_APP_TOKEN=xxx` 且 `config.yaml` 中 `feishu.bitable.app_token` 为空
- **THEN** 最终配置中 `feishu.bitable.app_token` SHALL 为 `xxx`

#### Scenario: 环境变量为空时回退
- **WHEN** `.env` 中 `FEISHU_BITABLE_APP_TOKEN` 未设置或为空
- **THEN** 最终配置 SHALL 使用 `config.yaml` 中的值

## ADDED Requirements

### Requirement: config.yaml.example 模板

系统 SHALL 提供 `config.yaml.example` 文件，包含所有配置项的结构和注释，敏感字段值使用占位符。

#### Scenario: 新环境部署
- **WHEN** 新用户克隆仓库
- **THEN** 可通过 `cp config.yaml.example config.yaml` 创建配置文件，按注释说明填写非敏感配置，敏感凭证通过 `.env` 提供
