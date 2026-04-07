# Proposal: 修复 config.yaml 凭证泄露风险

## Why

当前 `config.yaml` 文件中包含了真实的敏感凭证信息（飞书多维表格 `app_token`、`table_id` 以及钉钉机器人 `webhook_url`）。该文件虽然已被 `.gitignore` 排除，但仍存在以下安全风险：

1. **误提交风险**：`.gitignore` 规则可能被意外修改或绕过，导致真实凭证被提交到 Git 仓库历史中，难以彻底清除。
2. **配置分享风险**：团队成员或部署场景中需要共享 `config.yaml` 时，敏感信息会随之泄露。
3. **职责混淆**：当前架构已通过 `SecretConfig`（基于 `pydantic-settings`）从 `.env` 读取 `tikhub_api_key`、`feishu_app_id` 等凭证，但 `app_token`、`table_id`、`webhook_url` 仍残留在 `config.yaml` 中，破坏了"敏感信息集中在 `.env`、非敏感配置集中在 `config.yaml`"的职责分离原则。

## What Changes

1. **凭证迁移**：将 `config.yaml` 中的敏感字段（`feishu.bitable.app_token`、`feishu.bitable.table_id`、`dingtalk_worker.webhook_url`）迁移到 `.env` 文件，分别对应环境变量 `FEISHU_BITABLE_APP_TOKEN`、`FEISHU_BITABLE_TABLE_ID`、`DINGTALK_WEBHOOK_URL`。
2. **创建 `config.yaml.example`**：提供不含真实凭证的示例配置文件，作为新环境部署的参考模板。所有敏感字段替换为占位符并注明对应的环境变量名。
3. **更新 `config.py`**：在 `SecretConfig` 中新增 `feishu_bitable_app_token`、`feishu_bitable_table_id`、`dingtalk_webhook_url` 字段；修改 `load_config()` 逻辑，使飞书和钉钉的配置项从环境变量注入而非 YAML 读取。
4. **更新 `.env.example`**：添加新增的环境变量条目及说明注释。
5. **确认 `.gitignore`**：确保 `config.yaml` 和 `.env` 均已被排除（当前已包含，无需修改）。

## Capabilities

### New Capabilities

无新增能力。

### Modified Capabilities

**config-loading（配置加载）**

- **变更前**：`config.yaml` 包含飞书 `app_token`、`table_id` 和钉钉 `webhook_url` 等敏感字段，`load_config()` 直接从 YAML 读取这些值。
- **变更后**：所有敏感凭证统一通过 `.env` 环境变量提供，`SecretConfig` 新增对应的 Pydantic 字段。`config.yaml` 仅保留非敏感的运行参数（如端点地址、超时时间、文件路径等）。`load_config()` 合并逻辑调整为：敏感字段优先从环境变量读取，YAML 中的占位值被忽略。

## Impact

### 受影响文件

| 文件 | 变更类型 | 说明 |
|------|----------|------|
| `src/hot_pulse/config.py` | 修改 | `SecretConfig` 新增字段，`load_config()` 调整凭证注入逻辑 |
| `.env` | 修改 | 新增 `FEISHU_BITABLE_TABLE_ID` 等环境变量 |
| `.env.example` | 修改 | 添加新增环境变量的模板条目 |
| `config.yaml.example` | 新增 | 无真实凭证的配置模板 |
| `config.yaml` | 用户操作 | 用户需手动迁移敏感值到 `.env`，并将 `config.yaml` 中对应字段替换为占位符 |

### 不受影响

- 各 Worker 的业务逻辑无需修改，仅通过 `load_config()` 获取配置，接口不变。
- ZMQ、调度、监控等子系统配置不涉及敏感信息，保持不变。
