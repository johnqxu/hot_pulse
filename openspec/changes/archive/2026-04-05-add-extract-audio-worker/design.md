## Context

download worker 下载视频后通过 ZMQ 将 Task 发送给下游。 pipeline 当前缺少 extract_audio worker，需要从下载的视频文件中提取音频。

当前 STAGE_MAPPING 已定义 extract_audio 阶段的配置：
- inputs: `video_file` (上一阶段 download 的 output)
- outputs: `audio_file`
- next_type: transcribe

端口链路: download PUSH → 5552 → extract_audio pull → 5553 → transcribe

`run_worker()` 通用框架已成熟，download worker 已验证可用。

只需提供 handler 函数和配置即可。

## Goals / Non-Goals

**Goals:**
- 实现 extract_audio worker handler: 输入 video_file，输出 audio_file
- 使用 subprocess 调用 ffmpeg CLI 揬音频提取为 MP3 格式
- 新增 ExtractAudioWorkerConfig 配置类
- 在 config.yaml 中配置 extract_audio_worker 参数

**Non-Goals:**
- 不实现音频质量参数配置（使用默认参数即可)
- 不实现进度上报或音频提取过程较长)

不做进度条)

## Decisions

### D1: ffmpeg 调用方式

使用 `subprocess.run()` 贃用 ffmpeg CLI:

```python
cmd = ["ffmpeg", "-i", video_file, "-vn", audio_file, "-q:a", "0"]
```

 None`: ffmpeg 辴用的其他部分避免不必要的依赖。

简单直接。

### D2: 音频参数

- 格式: MP3
- 比特 比特特192k (默认, libmp3)
- 输出目录: `D:\batch\audio\{video_id}.mp3`

### D3: Worker 配置

```yaml
extract_audio_worker:
  pull_endpoint: "tcp://127.0.0.1:5552"
  push_endpoint: "tcp://127.0.0.1:5553"
  audio_dir: "D:\batch\audio"
```

### D4: handler 签名

```python
def handle_extract_audio(task: Task, config) -> dict[str, Any]:
    video_file = task.inputs.get("video_file", "")
    if not video_file:
        raise RuntimeError("Task inputs 中无 video_file")

    audio_file = _extract_audio(video_file, config.extract_audio_worker.audio_dir)
 config.extract_audio_worker.audio_format)
    return {"audio_file": audio_file}
```

## Risks / Trade-offs

- **[ffmpeg 未安装]** → 风险较低，用户需自行安装 ffmpeg 到 检查: 运行环境要求