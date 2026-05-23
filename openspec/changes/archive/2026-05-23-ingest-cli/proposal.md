## Why

当前 Hot Pulse 只能通过 TikTok 定时监控（monitor）发现新视频。缺少一条让用户手动提交感兴趣视频的入口。用户通过 OpenClaw 发现值得学习的 B站视频后，需要一个 CLI 命令将视频送入现有处理管道（下载 → 音频提取 → 文字转写），最终产出知识笔记。

## What Changes

- 新增 `ingest.py` CLI 入口：`python -m hot_pulse ingest --type video --platform bilibili --url ...`
- 集成 `yt-dlp` 解析 B站分享链接 → 提取直链、title、video_id
- 构造 `Task(source="manual", ...)` 并通过 ZMQ PUSH 推入 5551（对接 download_worker）
- `pyproject.toml` 新增 `yt-dlp` 依赖

## Capabilities

### New Capabilities

- `ingest-cli`: 手动提交视频内容的 CLI 入口，接收分享链接，通过 yt-dlp 解析后送入现有管道

### Modified Capabilities

（无）

## Impact

- **代码**: 新增 `ingest.py`（约 60 行），不修改任何现有文件
- **依赖**: 新增 `yt-dlp`（纯 Python，MIT 协议）
- **管道**: 复用现有 download → extract_audio → transcribe 链路，无改动
- **Task.source**: 依赖 Proposal 1 (`task-source-field`)，构造时传入 `source="manual"`
