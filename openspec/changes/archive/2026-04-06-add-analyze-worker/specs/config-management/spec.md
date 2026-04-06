## ADDED Requirements

### Requirement: AnalyzeWorkerConfig
系统 SHALL 提供 AnalyzeWorkerConfig 继承 WorkerConfig，包含 report_dir、model 和 prompt 配置。

#### Scenario: analyze_worker 配置
- **WHEN** config.yaml 中配置了 analyze_worker
- **THEN** 系统 SHALL 将其解析为 AnalyzeWorkerConfig，包含 pull_endpoint、push_endpoint、report_dir、model 和 prompt

#### Scenario: report_dir 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.report_dir
- **THEN** report_dir SHALL 默认为 `D:\batch\report`

#### Scenario: model 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.model
- **THEN** model SHALL 默认为 `"glm-5.1"`

#### Scenario: prompt 缺省
- **WHEN** config.yaml 中未配置 analyze_worker.prompt
- **THEN** 系统 SHALL 使用内置默认 prompt

### Requirement: zhipu_api_key 凭证
系统 SHALL 从 .env 文件加载可选的 ZHIPU_API_KEY，用于认证智谱 AI API 调用。

#### Scenario: 成功加载 ZHIPU_API_KEY
- **WHEN** .env 文件包含有效的 ZHIPU_API_KEY
- **THEN** 系统 SHALL 将其用于智谱 AI API 的 Authorization 请求头

#### Scenario: 缺少 ZHIPU_API_KEY
- **WHEN** .env 文件中未配置 ZHIPU_API_KEY
- **THEN** 系统 SHALL 允许启动，仅在 analyze worker 实际调用 API 时才抛出错误
