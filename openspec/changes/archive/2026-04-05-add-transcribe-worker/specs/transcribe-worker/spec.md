## ADDED Requirements

### Requirement: transcribe worker handler
系统 SHALL 提供 transcribe worker 的 handler 函数，从 Task.inputs 中获取 audio_file，使用 faster-whisper 将音频转写为简体中文纯文本。

#### Scenario: 成功转写音频
- **WHEN** Task.inputs 包含有效的 audio_file 路径（16kHz WAV 格式）
- **THEN** 系统 SHALL 使用 faster-whisper 加载配置中指定的模型（model_size）
- **AND** 以 language="zh" 参数调用 transcribe，关闭语言自动检测
- **AND** 将转写文本保存为 `{text_dir}/{video_id}.txt`
- **AND** 返回 {"text_file": text_file_path}

#### Scenario: audio_file 不存在
- **WHEN** Task.inputs 中无 audio_file
- **THEN** 系统 SHALL 抛出 RuntimeError

#### Scenario: 音频文件路径不存在于磁盘
- **WHEN** audio_file 指向的文件在磁盘上不存在
- **THEN** 系统 SHALL 抛出 RuntimeError

### Requirement: OpenVINO 加速与 CPU 降级
系统 SHALL 在首次加载模型时探测 OpenVINO 后端可用性，成功则使用 OpenVINO 加速，失败则降级到 CPU。

#### Scenario: OpenVINO 可用
- **WHEN** 系统首次加载模型且 OpenVINO 后端初始化成功
- **THEN** 系统 SHALL 使用 device="openvino"、compute_type="int8" 加载模型
- **AND** 记录日志 "OpenVINO 加速已启用"

#### Scenario: OpenVINO 不可用
- **WHEN** 系统首次加载模型且 OpenVINO 后端初始化失败
- **THEN** 系统 SHALL 降级使用 device="cpu"、compute_type="int8" 加载模型
- **AND** 记录警告日志说明 OpenVINO 不可用，已降级到 CPU

### Requirement: 模型实例全局缓存
系统 SHALL 将 faster-whisper 模型实例缓存在模块级全局变量中，整个 worker 生命周期只加载一次。

#### Scenario: 首次调用加载模型
- **WHEN** handler 首次被调用
- **THEN** 系统 SHALL 初始化 WhisperModel 实例并缓存到模块级变量

#### Scenario: 后续调用复用模型
- **WHEN** handler 后续被调用
- **THEN** 系统 SHALL 直接复用已缓存的模型实例，不重新加载

### Requirement: transcribe worker 独立运行入口
系统 SHALL 支持通过 `python -m hot_pulse.transcribe_worker` 独立启动 transcribe worker。

#### Scenario: 以 CLI 方式运行
- **WHEN** 用户执行 `python -m hot_pulse.transcribe_worker`
- **THEN** 系统 SHALL 调用 `run_worker("transcribe", handle_transcribe)`
