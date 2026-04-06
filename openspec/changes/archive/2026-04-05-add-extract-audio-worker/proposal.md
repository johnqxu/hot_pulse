## Why

视频下载完成后，需要从视频中提取音频供后续转写阶段使用。当前 pipeline 只有 download worker，extract_audio 阶段没有 worker 实现。需要新增 extract_audio worker，接收 download 宺段产出的 video_file，使用 ffmpeg 揄取音频并输出 audio_file。

## What Changes

- 新增 `extract_audio_worker.py`：extract_audio worker 的 handler 实现，使用 subprocess 调用 ffmpeg CLI 从视频中提取 MP3 音频
- 修改 `config.py`：新增 `ExtractAudioWorkerConfig` 配置类
- 修改 `config.yaml`：新增 `extract_audio_worker` 配置段

## Capabilities

### New Capabilities

- `extract-audio-worker`: 音频提取 worker，从下载的视频文件中提取 MP3 音频

### Modified Capabilities
- `config-management`: 新增 ExtractAudioWorkerConfig 配置

## Impact

- 新增文件：`extract_audio_worker.py`
- 修改文件：`config.py`、`config.yaml`
- 外部依赖：系统需安装 ffmpeg
- 无新增 pip 依赖
