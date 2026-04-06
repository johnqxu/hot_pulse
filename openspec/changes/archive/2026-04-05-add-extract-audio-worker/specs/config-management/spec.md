## MODIFIED Requirements

### Requirement: Extract_audio_worker config
系统 SHALL 提供 ExtractAudioWorkerConfig 继承 WorkerConfig，包含 audio_dir 配置。

#### Scenario: extract_audio_worker 配置
- **WHEN** config.yaml 中配置了 extract_audio_worker
- **THEN** 系统 SHALL 将其解析为 ExtractAudioWorkerConfig，包含 pull_endpoint、push_endpoint 和 audio_dir

#### Scenario: audio_dir 缺省
- **WHEN** config.yaml 中未配置 extract_audio_worker.audio_dir
- **THEN** audio_dir SHALL 默认为 `D:\batch\audio`
