## MODIFIED Requirements

### Requirement: AnalyzeWorkerConfig
系统 SHALL 提供 AnalyzeWorkerConfig 继承 WorkerConfig，包含 report_dir、model、prompt、openai_base_url、reasoning_effort 和 extra_body 配置。

#### Scenario: analyze_worker 配置
- **WHEN** config.yaml 中配置了 analyze_worker
- **THEN** 系统 SHALL 将其解析为 AnalyzeWorkerConfig，包含 pull_endpoint、push_endpoint、report_dir、model、prompt、openai_base_url、reasoning_effort 和 extra_body

#### Scenario: report_dir 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.report_dir
- **THEN** report_dir SHALL 默认为 `D:\batch\report`

#### Scenario: model 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.model
- **THEN** model SHALL 默认为 `"deepseek-v4-flash"`

#### Scenario: prompt 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.prompt
- **THEN** 系统 SHALL 使用内置默认 prompt

#### Scenario: openai_base_url 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.openai_base_url
- **THEN** openai_base_url SHALL 默认为 `"https://api.deepseek.com/v1"`

#### Scenario: reasoning_effort 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.reasoning_effort
- **THEN** reasoning_effort SHALL 默认为 `"high"`

#### Scenario: extra_body 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.extra_body
- **THEN** extra_body SHALL 默认为空 dict `{}`

### Requirement: 从 .env 文件加载敏感凭证
系统 SHALL 从项目根目录的 `.env` 文件加载敏感凭证（TikHub API Key、飞书 App ID、飞书 App Secret、飞书 Bitable App Token、飞书 Bitable Table ID、钉钉 Webhook URL、OpenAI API Key），与 YAML 配置分开管理。

#### Scenario: 成功加载有效的 .env 文件
- **WHEN** 存在包含所有必填 key 的有效 `.env` 文件（TIKHUB_API_KEY, FEISHU_APP_ID, FEISHU_APP_SECRET）
- **THEN** 系统 SHALL 加载凭证并供需要的模块使用
- **AND** OPENAI_API_KEY 为可选字段，缺失时允许启动

#### Scenario: .env 文件缺少必填 key
- **WHEN** `.env` 文件缺失或不包含所有必填 key
- **THEN** 系统 SHALL 抛出清晰的错误信息，列出缺失的 key

### Requirement: openai_api_key 凭证
系统 SHALL 从 .env 文件加载可选的 OPENAI_API_KEY，用于认证 OpenAI 兼容的 LLM API 调用。

#### Scenario: 成功加载 OPENAI_API_KEY
- **WHEN** .env 文件包含有效的 OPENAI_API_KEY
- **THEN** 系统 SHALL 将其用于 LLM API 的 Authorization 请求头

#### Scenario: 缺少 OPENAI_API_KEY
- **WHEN** .env 文件中未配置 OPENAI_API_KEY
- **THEN** 系统 SHALL 允许启动，仅在 analyze worker 实际调用 API 时才抛出错误

## REMOVED Requirements

### Requirement: zhipu_api_key 凭证
**Reason**: 替换为通用的 openai_api_key 凭证，不再绑定智谱 AI 专用 Key 名称
**Migration**: 将 `.env` 中的 `ZHIPU_API_KEY` 重命名为 `OPENAI_API_KEY`，并填入 DeepSeek 或其他厂商的 API Key
