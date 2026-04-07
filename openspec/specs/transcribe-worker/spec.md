## Purpose

transcribe worker 负责将音频文件转写为简体中文纯文本，使用 faster-whisper 模型，支持 OpenVINO 加速与 CPU 降级。

## Requirements

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
系统 SHALL 在首次加载模型时探测 OpenVINO 后端可用性，成功则使用 OpenVINO GPU 加速（OVWhisperModel），失败则降级到 CPU（FasterWhisperModel）。

OVWhisperModel SHALL 将音频按 30 秒固定窗口切分为不重叠片段，逐段执行 encoder-decoder 推理，拼接完整转写文本。

#### Scenario: OpenVINO GPU 可用 — 短音频（≤30 秒）
- **WHEN** 音频时长 ≤ 30 秒且 OVWhisperModel 已加载
- **THEN** 系统 SHALL 将整段音频送入 encoder 做 1 次推理
- **AND** decoder SHALL 以 max_tokens=448 为上限生成文本

#### Scenario: OpenVINO GPU 可用 — 长音频（>30 秒）
- **WHEN** 音频时长 > 30 秒且 OVWhisperModel 已加载
- **THEN** 系统 SHALL 将音频按 30 秒窗口切分为 N 个片段
- **AND** 每个片段独立执行 encoder-decoder 推理
- **AND** 跳过解码结果为空的片段
- **AND** 非空片段用换行符拼接为完整文本

#### Scenario: 分片边界处理
- **WHEN** 某个 30 秒片段包含静音或纯噪声
- **THEN** decoder SHALL 返回空文本
- **AND** 系统 SHALL 跳过该片段，不输出空行

#### Scenario: OpenVINO 不可用
- **WHEN** 系统首次加载模型且 OpenVINO 后端初始化失败
- **THEN** 系统 SHALL 降级使用 FasterWhisperModel（faster-whisper, device="cpu", compute_type="int8"）
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
