## Purpose

extract_audio worker 负责从已下载的视频文件中提取音频，使用 ffmpeg 转换为 16kHz 单声道 WAV 格式，供后续音频转写阶段使用。

## Requirements

### Requirement: extract_audio worker handler
系统 SHALL 提供 extract_audio worker 的 handler 函数，从 Task.inputs 中获取 video_file，使用 ffmpeg 提取 16kHz 单声道 WAV 格式音频。

#### Scenario: 成功提取音频
- **WHEN** Task.inputs 包含有效的 video_file 路径
- **THEN** 系统 SHALL 使用 ffmpeg 提取音频并保存为 `{audio_dir}/{video_id}.wav`
- **AND** ffmpeg 参数 SHALL 包含 `-ar 16000 -ac 1`（16kHz 采样率、单声道）
- **AND** 返回 {"audio_file": audio_file_path}

#### Scenario: video_file 不存在
- **WHEN** Task.inputs 中无 video_file
- **THEN** 系统 SHALL 抛出 RuntimeError

#### Scenario: ffmpeg 未安装
- **WHEN** 系统中未安装 ffmpeg
- **THEN** 系统 SHALL 在 worker 启动时记录错误日志并快速失败
