## Context

用户通过 OpenClaw Skill 发现感兴趣的视频内容后，需要一条 CLI 路径将视频提交到 Hot Pulse 处理管道。当前系统只有 `monitor` 主动轮询 TikTok 这一条入口。

## Goals / Non-Goals

**Goals:**
- 提供 `python -m hot_pulse ingest` CLI，接收分享链接、平台、备注等参数
- 用 `yt-dlp --dump-json` 解析 B站分享链接，提取直链 URL、title、video_id
- 构造 Task 并通过 ZMQ 推入 5551，对接现有 download_worker → 管道
- title 为可选参数，未传时用 yt-dlp 输出的标题
- 临时进程：推完 Task 立即退出

**Non-Goals:**
- 不支持 `type=article`（留给后续 proposal）
- 不支持 B站以外的平台（MVP 仅 B站）
- 不改造 download_worker 的 URL 优先级排序逻辑
- 不做任务进度查询（仅返回 task_id）

## Decisions

### 1. CLI 参数设计

```bash
python -m hot_pulse ingest \
  --type video \              # 必填，先只支持 video
  --platform bilibili \       # 必填，先只支持 bilibili
  --url "https://..." \       # 必填，分享链接
  --title "..." \             # 可选，不传则由 yt-dlp 提取
  --notes "..."               # 可选，写入 Task.inputs.notes
```

### 2. yt-dlp 集成方式

```
subprocess.run(["yt-dlp", "--dump-json", url], capture_output=True)
→ 解析 JSON
→ 提取: direct_url, title, video_id(从 webpage_url/id 等字段)
```

yt-dlp JSON 输出包含 `title`、`id`、`webpage_url`、`formats[].url` 等字段，一次性拿到所有需要的信息。

### 3. Task 构造

```python
task = Task(
    task_id=str(uuid.uuid4()),
    task_type="download",
    video_id=video_id,          # yt-dlp 输出的 id
    creator="",                 # manual 不填
    title=args.title or yt_title,
    platform=args.platform,
    source="manual",
    inputs={
        "play_urls": [direct_url],
        "notes": args.notes or "",
    },
)
```

### 4. ZMQ 推送

复用 `ZmqPublisher`，连到 `config.zeromq.push_endpoint`（`tcp://127.0.0.1:5551`），推完 Task 关闭连接退出。

### 5. 输出

成功时 stdout 输出 JSON：
```json
{"task_id": "a1b2c3d4", "status": "submitted"}
```
失败时 stderr 日志 + 非零退出码。

## Risks / Trade-offs

- **[风险] yt-dlp 直链时效性**：B站直链几小时过期 → **缓解**：手动提交场景下 worker 应在数分钟内开始下载，时效够用
- **[取舍] 仅 B站 MVP**：后续 proposal 扩展 platform 支持
