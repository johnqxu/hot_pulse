## Why

流水线已有 download → extract_audio 两阶段运行，但音频文件尚未被转化为可分析的文本。transcribe worker 是连接音频提取和内容分析的关键阶段，将音频转写为简体中文纯文本，供下游 analyze worker 使用大模型进行分析。

## What Changes

- 新建 `transcribe_worker.py`，使用 `faster-whisper` 库调用本地 Whisper 模型进行语音转写
- 优先使用 OpenVINO 后端加速（利用 Intel Iris Xe 集成显卡），启动时自动探测，不支持则降级为 CPU
- 模型通过模块级全局变量缓存，整个 worker 生命周期只加载一次
- 修改 `extract_audio_worker.py`，将音频输出格式从 MP3 改为 16kHz 单声道 WAV（Whisper 推荐输入格式）
- 新增依赖 `faster-whisper` 到 `pyproject.toml`
- `TranscribeWorkerConfig` 增加 `model_size` 配置项（默认 `"medium"`）
- `config.yaml` 的 `transcribe_worker` 段增加 `model_size` 字段

## Capabilities

### New Capabilities
- `transcribe-worker`: 使用 faster-whisper 将音频转写为简体中文纯文本，支持 OpenVINO 加速和 CPU 降级

### Modified Capabilities
- `extract-audio-worker`: 音频输出格式从 MP3 改为 16kHz 单声道 WAV
- `config-management`: TranscribeWorkerConfig 新增 model_size 字段

## Impact

- **新增依赖**: `faster-whisper`（及其间接依赖 `ctranslate2`）
- **修改文件**: `extract_audio_worker.py`、`config.py`、`config.yaml`、`pyproject.toml`
- **前置条件**: 系统需安装 ffmpeg（已有）
- **流水线位置**: extract_audio(5552) → **transcribe(5553)** → analyze(5554)
- **非目标**: 不实现时间戳输出、不实现多语言支持、不实现 GPU（NVIDIA CUDA）支持
