## MODIFIED Requirements

### Requirement: DownloadWorkerConfig
系统 SHALL 提供 DownloadWorkerConfig 继承 WorkerConfig，包含 download_dir 和 url_priority 配置。

#### Scenario: url_priority 配置
- **WHEN** config.yaml 中配置了 download_worker.url_priority
- **THEN** 系统 SHALL 将其解析为 dict[str, int]，key 为域名模式（支持 `*` 通配符前缀），value 为优先级数值

#### Scenario: url_priority 缺省
- **WHEN** config.yaml 中未配置 download_worker.url_priority
- **THEN** url_priority SHALL 默认为空 dict，所有 URL 优先级均为 0
