## Context

`config.yaml` 目前包含飞书 `app_token`、`table_id` 和钉钉 `webhook_url` 等敏感信息。虽然已被 `.gitignore` 排除，但 .gitignore 是事后添加的，git 历史中可能已有泄漏。需要将这些字段迁移到 `.env`，并创建不含凭证的 `config.yaml.example` 供模板使用。

当前架构已有 `SecretConfig`（pydantic-settings）从 `.env` 读取敏感字段，只需扩展即可。

## Goals / Non-Goals

**Goals:**
- 将 `config.yaml` 中的 `feishu.bitable.app_token`、`feishu.bitable.table_id`、`dingtalk_worker.webhook_url` 迁移到 `.env`
- `SecretConfig` 新增对应字段
- 创建 `config.yaml.example` 模板
- 清理 git 历史中的敏感信息

**Non-Goals:**
- 不改变各 worker 的配置读取接口
- 不引入加密或密钥管理服务
- 不修改 worker 业务逻辑

## Decisions

### 1. 凭证迁移到 SecretConfig

在 `SecretConfig` 中新增三个字段：

```python
class SecretConfig(BaseSettings):
    # 已有
    tikhub_api_key: str
    feishu_app_id: str
    feishu_app_secret: str
    # 新增
    feishu_bitable_app_token: str = ""
    feishu_bitable_table_id: str = ""
    dingtalk_webhook_url: str = ""
```

`load_config()` 中将 `secrets` 的值注入到 `FeishuConfig` 和 `DingTalkWorkerConfig`，覆盖 YAML 中的占位值。

### 2. config.yaml 保留结构但值变为占位符

`config.yaml` 中的敏感字段保留 key 结构但值为空字符串或占位符：

```yaml
feishu:
  bitable:
    app_token: ""    # 从 .env 读取 FEISHU_BITABLE_APP_TOKEN
    table_id: ""     # 从 .env 读取 FEISHU_BITABLE_TABLE_ID

dingtalk_worker:
  webhook_url: ""    # 从 .env 读取 DINGTALK_WEBHOOK_URL
```

### 3. load_config() 合并逻辑

在 `load_config()` 中，secrets 创建后，用 secrets 的值覆盖 YAML 解析出的配置：

```python
config.feishu.bitable.app_token = config.secrets.feishu_bitable_app_token or config.feishu.bitable.app_token
```

优先使用 .env 值，若为空则回退到 YAML 值（兼容旧配置）。

### 4. git 历史清理

由于 config.yaml 已经被推送到远程仓库（包含真实凭证），需要：
- 确保 config.yaml 已在 .gitignore 中
- 使用 `git filter-branch` 或 `BFG Repo-Cleaner` 清理历史
- 或者更简单的方案：删除远程仓库重建（因为是私有仓库且刚创建）

## Risks / Trade-offs

- **[向后兼容]** → 旧配置方式（YAML 中直接写凭证）仍可工作，secrets 为空时回退到 YAML 值
- **[git 历史清理]** → 需要用户确认是否清理历史或重建仓库
