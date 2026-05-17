## Purpose

提供通用 OpenAI 兼容的 LLM 调用层，通过配置切换 DeepSeek、智谱、OpenAI 等不同大模型提供商，无需修改代码。

## ADDED Requirements

### Requirement: 通用 OpenAI 兼容 API 调用

系统 SHALL 使用可配置的 `openai_base_url` 和 `openai_api_key` 调用 LLM API，请求/响应格式遵循 OpenAI chat/completions 规范。

#### Scenario: 正常 API 调用
- **WHEN** analyze worker 需要调用 LLM 生成分析报告
- **THEN** 系统 SHALL 使用 POST 方法调用 `{openai_base_url}/chat/completions`
- **AND** 请求头包含 `Authorization: Bearer {openai_api_key}`
- **AND** 请求体包含 model、messages（system prompt + user message）、temperature 参数
- **AND** 从响应 JSON 的 `choices[0].message.content` 中提取完整响应文本

#### Scenario: 响应解析与摘要提取
- **WHEN** LLM API 返回 200 状态码
- **THEN** 系统 SHALL 从响应 JSON 的 `choices[0].message.content` 中提取完整响应文本
- **AND** 系统 SHALL 解析首行的 `<<<SUMMARY>>>...<<<END>>>` 标记提取 10 字摘要用于文件名
- **AND** 剩余行作为报告正文

#### Scenario: API Key 未配置
- **WHEN** `.env` 中未设置 `OPENAI_API_KEY` 或值为空
- **THEN** 系统 SHALL 在 analyze worker 实际调用 API 时抛出错误，提示 Key 未配置

#### Scenario: API 调用失败
- **WHEN** LLM API 返回非 200 状态码或网络异常
- **THEN** 系统 SHALL 抛出包含状态码和错误信息的异常
- **AND** 错误信息中 SHALL 包含 HTTP 状态码和响应体概要（截取前 500 字符）

### Requirement: reasoning_effort 参数支持

系统 SHALL 支持在请求体中传递 `reasoning_effort` 参数，控制模型的推理深度。

#### Scenario: 传递 reasoning_effort
- **WHEN** `config.yaml` 中 `analyze_worker.reasoning_effort` 配置为非空值（如 `"high"` 或 `"max"`）
- **THEN** 系统 SHALL 将该值作为请求体的 `reasoning_effort` 字段发送
- **AND** 该字段 SHALL 位于请求体顶层（与 model、messages 同级）

#### Scenario: reasoning_effort 未配置
- **WHEN** `config.yaml` 中未配置 `reasoning_effort` 或配置为空字符串
- **THEN** 系统 SHALL 不发送 `reasoning_effort` 字段

### Requirement: extra_body 厂商专属参数支持

系统 SHALL 支持通过 `extra_body` 配置字典传递厂商专属参数到请求体。

#### Scenario: 传递厂商专属参数
- **WHEN** `config.yaml` 中 `analyze_worker.extra_body` 配置为非空 dict
- **THEN** 系统 SHALL 将该 dict 的键值对合并到请求体中
- **AND** 若键与标准字段重复，extra_body 的值 SHALL 覆盖标准字段

#### Scenario: extra_body 未配置
- **WHEN** `config.yaml` 中未配置 `extra_body` 或配置为空 dict
- **THEN** 系统 SHALL 不添加任何额外字段到请求体

#### Scenario: DeepSeek thinking 模式
- **WHEN** 使用 DeepSeek 提供商且配置 `extra_body.thinking.type` 为 `"enabled"`
- **THEN** 系统 SHALL 将 `{"thinking": {"type": "enabled"}}` 合并到请求体
- **AND** 模型将在响应中输出 `<think>...</think>` 推理链标签

### Requirement: 内置默认 Prompt

系统 SHALL 内置财经分析师角色 Prompt，当 `config.yaml` 中未配置自定义 prompt 时使用。

#### Scenario: 使用内置 Prompt
- **WHEN** `config.yaml` 中 `analyze_worker.prompt` 为空字符串
- **THEN** 系统 SHALL 使用内置的财经分析师 Prompt
- **AND** Prompt 要求模型首行输出 `<<<SUMMARY>>>...<<<END>>>` 摘要行
- **AND** Prompt 要求模型输出六章节：内容摘要、推荐板块、推荐个股（A股/港股）、风险提示、操作建议、标签

#### Scenario: 使用自定义 Prompt
- **WHEN** `config.yaml` 中 `analyze_worker.prompt` 为非空字符串
- **THEN** 系统 SHALL 使用自定义 Prompt 作为 system message
