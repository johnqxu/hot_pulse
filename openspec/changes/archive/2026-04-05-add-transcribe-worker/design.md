## Context

流水线已完成 download → extract_audio 两个阶段，音频文件以 MP3 格式存储在本地。现需实现 transcribe worker，将音频转写为简体中文纯文本，供下游 analyze worker 使用大模型分析。

当前 extract_audio worker 使用 ffmpeg 输出 MP3 格式，而 Whisper 模型推荐 16kHz WAV 输入。本变更同时调整 extract_audio 的输出格式。

运行环境：Windows 11，i7-1165G7 + Iris Xe 集成显卡，无独立 GPU。

## Goals / Non-Goals

**Goals:**
- 实现音频转写为简体中文纯文本
- 利用 Intel Iris Xe 集成显卡通过 OpenVINO 加速推理
- 不支持 OpenVINO 时自动降级到 CPU
- 调整 extract_audio 输出格式为 16kHz 单声道 WAV
- 模型实例全局缓存，避免重复加载

**Non-Goals:**
- 不实现时间戳/字幕输出
- 不实现多语言支持
- 不支持 NVIDIA CUDA GPU
- 不实现流式/实时转写

## Decisions

### 1. Whisper 实现选择：faster-whisper

**选择**: `faster-whisper`（基于 CTranslate2）

**备选**:
- `openai-whisper`：官方实现，但速度慢 3-4 倍
- `whisper.cpp`：CPU 上略快，但 Windows 安装复杂，Python 集成不如 faster-whisper

**理由**: faster-whisper 在 CPU 和 Intel iGPU 上都有良好支持（OpenVINO 后端），pip 安装简单，Python API 干净。与项目现有依赖管理方式（uv）一致。

### 2. 设备策略：OpenVINO 探测 + CPU 降级

**选择**: 启动时尝试 `device="openvino"`，失败则降级 `device="cpu"`

**理由**: 不增加配置项。如果硬件支持 OpenVINO（11代 i7 Iris Xe 支持），所有任务都用加速；不支持则全部用 CPU。这是运行时环境的能力，不需要用户配置。

### 3. 模型加载策略：模块级全局缓存

**选择**: 模块级 `_model` 变量，首次调用时初始化，整个 worker 生命周期复用

```python
_model = None

def _get_model(config):
    global _model
    if _model is None:
        _model = _init_model(config)
    return _model
```

**理由**: faster-whisper 模型加载需要数秒到数十秒（首次还需下载），每条任务都加载不可接受。模块级缓存简单可靠，worker 是单进程顺序处理，无需担心并发。

### 4. 音频格式：16kHz 单声道 WAV

**选择**: 修改 extract_audio worker，ffmpeg 输出从 MP3 改为 16kHz WAV

**理由**: Whisper 内部会将输入转为 16kHz WAV。预先提供此格式可跳过 faster-whisper 内部的 ffmpeg 重采样步骤，减少 IO 和计算开销。单声道（`-ac 1`）进一步减小文件体积。

### 5. 配置项：model_size 可配置

**选择**: TranscribeWorkerConfig 增加 `model_size: str = "medium"`

**理由**: 模型大小是用户最可能想调整的参数（medium vs large-v3）。放入配置比硬编码更灵活。

## Risks / Trade-offs

- **[OpenVINO 兼容性]** → 运行时自动降级到 CPU，不影响功能
- **[medium 模型中文精度]** → medium 中文偶有错字，large-v3 更好但 CPU 上慢 2-3 倍。用户可通过 model_size 配置切换
- **[首次模型下载]** → faster-whisper 首次运行会从 HuggingFace 下载模型（medium ~1.5GB），需要网络。后续使用本地缓存
- **[faster-whisper 依赖链]** → ctranslate2 是 C++ 库，pip wheel 在 Windows 上通常可用，但版本兼容需注意
