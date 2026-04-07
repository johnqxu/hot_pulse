## Why

OVWhisperModel（GPU 路径）将整个音频一次性送入 Whisper encoder，但 Whisper 的 positional embedding 最多支持 1500 帧（约 30 秒），超过部分被截断；同时 decoder 的 `max_tokens=448` 进一步截断输出。导致长视频（>30 秒）的文字转写严重不全，实际只输出前几秒到十几秒的内容。

## What Changes

- 重写 `OVWhisperModel.transcribe()`：将音频按 30 秒分片，逐段编码+解码，拼接完整文本
- 移除 `max_tokens=448` 硬限制，每段使用合理的 token 上限（如 448）
- 每段转写前通过能量检测或静音检测寻找分段边界，避免切断单词/句子
- 保持与 `FasterWhisperModel`（CPU 路径）相同的输出格式（纯文本，段落间换行）

## Capabilities

### New Capabilities

（无）

### Modified Capabilities

- `transcribe-worker`: 修改 OVWhisperModel 的转写逻辑，从单次整段推理改为分段切片推理

## Impact

- 文件：`src/hot_pulse/transcribe_worker.py`（OVWhisperModel 类）
- 无 API/配置变更，无需修改 config.yaml 或 .env
- 不影响 FasterWhisperModel（CPU 路径）
- 不影响下游 analyze_worker（输入格式不变）
