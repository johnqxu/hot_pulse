## Why

当前 analyze worker 硬编码绑定智谱 GLM API（URL 和 API Key 字段均专属），无法切换到其他大模型厂商。DeepSeek V4 系列在性价比、上下文窗口、推理能力方面表现突出，且其 API 为标准的 OpenAI 兼容格式——与智谱 GLM 的 chat/completions 格式实为同一规范。将 LLM 调用层抽象为通用 OpenAI 兼容接口，实现"切换模型只改配置"的灵活性。

## What Changes

- 新增 `openai_base_url` 和 `reasoning_effort` 配置字段，API URL 不再硬编码
- `ZHIPU_API_KEY` 环境变量重命名为 `OPENAI_API_KEY`（通用 API Key）— **BREAKING**
- `analyze_worker.model` 默认值从 `glm-5.1` 改为 `deepseek-v4-flash`
- API 调用方法从 `_call_glm_api` 重构为 `_call_llm_api`，URL 和 Key 从配置读取
- 新增 `extra_body` 配置字段，用于传递厂商专属参数（如 DeepSeek 的 `thinking` 开关）
- 配置文件 `config.yaml.example` 和 `.env.example` 同步更新

## Capabilities

### New Capabilities

- `openai-compatible-llm`: 通用 OpenAI 兼容的 LLM 调用层，支持通过配置切换不同的模型提供商（DeepSeek、智谱、OpenAI 等），无需修改代码

### Modified Capabilities

- `analyze-worker`: LLM API 调用从智谱专属改为通用 OpenAI 兼容格式；URL/Key/Model 全部由配置驱动
- `config-management`: 敏感凭证 `ZHIPU_API_KEY` 替换为通用的 `OPENAI_API_KEY`；`AnalyzeWorkerConfig` 新增 `openai_base_url`、`extra_body`、`reasoning_effort` 字段

## Impact

- **配置**: `config.yaml` 的 `analyze_worker` 段新增字段；`.env` 中 `ZHIPU_API_KEY` → `OPENAI_API_KEY`（不兼容旧配置，需手动迁移）
- **代码**: `analyze_worker.py` 的 `_call_glm_api` 方法重构；`config.py` 的 `SecretConfig` 和 `AnalyzeWorkerConfig` 修改
- **依赖**: 无新增外部依赖（httpx 已能满足需求）
- **部署**: 现有运维者需更新 `.env` 中的 Key 名称和值，并调整 `config.yaml` 中的 model 配置
