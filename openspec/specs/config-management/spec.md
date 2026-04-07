## Purpose

管理应用配置，从 YAML 文件加载非敏感设置，从 .env 文件加载敏感凭证，使用 pydantic-settings 进行类型安全校验和快速失败错误处理。

## Requirements

### Requirement: 从 YAML 文件加载非敏感配置
系统 SHALL 从项目根目录的 `config.yaml` 文件加载配置，包括：TikHub 基础 URL 和端点、飞书多维表格标识、创作者列表、调度设置、各阶段 worker 配置。

#### Scenario: 成功加载有效的 config.yaml
- **WHEN** 项目根目录存在包含所有必填字段的有效 `config.yaml`
- **THEN** 系统 SHALL 解析并校验配置为类型化的配置对象

#### Scenario: config.yaml 缺失或无效
- **WHEN** `config.yaml` 缺失或包含无效/缺失的必填字段
- **THEN** 系统 SHALL 抛出清晰的错误信息，说明缺失或无效的内容

#### Scenario: download_worker 配置段
- **WHEN** config.yaml 包含 download_worker 配置段
- **THEN** 系统 SHALL 加载 pull_endpoint、push_endpoint、download_dir 字段
- **AND** download_dir 默认值为 `D:\batch\video`
- **AND** DownloadWorkerConfig SHALL 继承 WorkerConfig 基类（pull_endpoint, push_endpoint）

### Requirement: DownloadWorkerConfig
系统 SHALL 提供 DownloadWorkerConfig 继承 WorkerConfig，包含 download_dir 和 url_priority 配置。

#### Scenario: url_priority 配置
- **WHEN** config.yaml 中配置了 download_worker.url_priority
- **THEN** 系统 SHALL 将其解析为 dict[str, int]，key 为域名模式（支持 `*` 通配符前缀），value 为优先级数值

#### Scenario: url_priority 缺省
- **WHEN** config.yaml 中未配置 download_worker.url_priority
- **THEN** url_priority SHALL 默认为空 dict，所有 URL 优先级均为 0

### Requirement: Extract_audio_worker config
系统 SHALL 提供 ExtractAudioWorkerConfig 继承 WorkerConfig，包含 audio_dir 配置。

#### Scenario: extract_audio_worker 配置
- **WHEN** config.yaml 中配置了 extract_audio_worker
- **THEN** 系统 SHALL 将其解析为 ExtractAudioWorkerConfig，包含 pull_endpoint、push_endpoint 和 audio_dir

#### Scenario: audio_dir 缺省
- **WHEN** config.yaml 中未配置 extract_audio_worker.audio_dir
- **THEN** audio_dir SHALL 默认为 `D:\batch\audio`

### Requirement: TranscribeWorkerConfig
系统 SHALL 提供 TranscribeWorkerConfig 继承 WorkerConfig，包含 text_dir 和 model_size 配置。

#### Scenario: transcribe_worker 配置
- **WHEN** config.yaml 中配置了 transcribe_worker
- **THEN** 系统 SHALL 将其解析为 TranscribeWorkerConfig，包含 pull_endpoint、push_endpoint、text_dir 和 model_size

#### Scenario: text_dir 缺省
- **WHEN** config.yaml 中未配置 transcribe_worker.text_dir
- **THEN** text_dir SHALL 默认为 `D:\batch\text`

#### Scenario: model_size 缺省
- **WHEN** config.yaml 中未配置 transcribe_worker.model_size
- **THEN** model_size SHALL 默认为 `"medium"`

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

### Requirement: 从 .env 文件加载敏感凭证
系统 SHALL 从项目根目录的 `.env` 文件加载敏感凭证（TikHub API Key、飞书 App ID、飞书 App Secret、飞书 Bitable App Token、飞书 Bitable Table ID、钉钉 Webhook URL），与 YAML 配置分开管理。

#### Scenario: 成功加载有效的 .env 文件
- **WHEN** 存在包含所有必填 key 的有效 `.env` 文件（TIKHUB_API_KEY, FEISHU_APP_ID, FEISHU_APP_SECRET）
- **THEN** 系统 SHALL 加载凭证并供需要的模块使用

#### Scenario: .env 文件缺少必填 key
- **WHEN** `.env` 文件缺失或不包含所有必填 key
- **THEN** 系统 SHALL 抛出清晰的错误信息，列出缺失的 key

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

### Requirement: config.yaml.example 模板
系统 SHALL 提供 `config.yaml.example` 文件，包含所有配置项的结构和注释，敏感字段值使用占位符。

#### Scenario: 新环境部署
- **WHEN** 新用户克隆仓库
- **THEN** 可通过 `cp config.yaml.example config.yaml` 创建配置文件，按注释说明填写非敏感配置，敏感凭证通过 `.env` 提供

### Requirement: zhipu_api_key 凭证
系统 SHALL 从 .env 文件加载可选的 ZHIPU_API_KEY，用于认证智谱 AI API 调用。

#### Scenario: 成功加载 ZHIPU_API_KEY
- **WHEN** .env 文件包含有效的 ZHIPU_API_KEY
- **THEN** 系统 SHALL 将其用于智谱 AI API 的 Authorization 请求头

#### Scenario: 缺少 ZHIPU_API_KEY
- **WHEN** .env 文件中未配置 ZHIPU_API_KEY
- **THEN** 系统 SHALL 允许启动，仅在 analyze worker 实际调用 API 时才抛出错误

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

### Requirement: 配置模型校验
系统 SHALL 使用 pydantic-settings 定义类型化配置模型，在加载时校验所有必填字段，遇到无效配置时快速失败。

#### Scenario: 创作者条目缺少必填字段
- **WHEN** config.yaml 中的创作者条目缺少 `name` 或 `sec_uid`
- **THEN** 系统 SHALL 抛出校验错误，标识无效的条目
