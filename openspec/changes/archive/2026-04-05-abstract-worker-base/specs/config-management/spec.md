## MODIFIED Requirements

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
- **AND** DownloadWorkerConfig SHALL 继承 WorkerConfig 基类（pull_endpoint, push_endpoint）
