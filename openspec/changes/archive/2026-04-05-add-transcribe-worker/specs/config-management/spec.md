## MODIFIED Requirements

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

## ADDED Requirements

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
