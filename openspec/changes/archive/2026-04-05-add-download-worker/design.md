## Context

监控阶段（monitor）已实现视频发现与 ZMQ Task 发送。download worker 是流水线第一个常驻消费者进程，负责接收 download 类型 Task、下载视频文件、更新飞书记录、构建并推送下一阶段 Task。

关键约束：
- download worker 是常驻进程，通过 ZMQ PULL 从 monitor 拉取任务
- 视频文件存储到本地文件系统 `D:\batch\video\{video_id}.mp4`
- 每个视频可能有多条 play_urls，需按顺序尝试
- httpx 已是项目依赖，使用流式下载避免大文件占满内存
- TaskManager 已封装 start/finish/fail/build_next，worker 直接复用

## Goals / Non-Goals

**Goals:**
- 实现常驻 download worker 进程，从 ZMQ 拉取 Task 并执行下载
- 使用 httpx 流式下载，遍历 play_urls 按顺序尝试
- 下载完成后更新飞书记录，向下游发送 extract_audio Task
- 在 config.yaml 中配置 worker 的 ZMQ 端点和下载目录

**Non-Goals:**
- 不实现断点续传
- 不实现下载限速
- 不实现多 worker 并发（单进程顺序处理）
- 不修改飞书表格结构

## Decisions

### D1: 下载策略 — 遍历 play_urls 逐个尝试

play_urls 列表中的 URL 按顺序优先级递减。httpx 流式下载单个 URL，失败后尝试下一个，全部失败则标记任务 failed。

选择此方案而非"仅尝试第一个"：CDN 链接有时效性和地域限制，提供备选可提高成功率。

### D2: 文件存储路径

路径格式：`{download_dir}/{video_id}.mp4`，其中 `download_dir` 从配置读取，默认 `D:\batch\video`。

- video_id 作为文件名天然唯一
- 不按 creator 分子目录，简化路径管理
- 目录不存在时自动创建

### D3: Worker 进程结构

```
download_worker.py
├── main()            # 入口，加载配置，创建依赖
├── _run_worker()     # 主循环：recv_task → start → download → finish → send_next
└── _download_video() # 纯下载逻辑：遍历 URLs，流式写入文件
```

worker 持有三类依赖：
- `ZmqConsumer(pull_endpoint)` — 拉取上游 Task
- `ZmqPublisher(push_endpoint)` — 推送下游 Task
- `TaskManager(feishu)` — 飞书同步

### D4: ZMQ 端点配置

在 config.yaml 新增 `download_worker` 配置段：

```yaml
download_worker:
  pull_endpoint: "tcp://127.0.0.1:5551"   # 从 monitor 拉取
  push_endpoint: "tcp://127.0.0.1:5552"   # 推给 extract_audio
  download_dir: "D:\\batch\\video"
```

与现有 `zeromq` 配置并列。monitor 的 PUSH 端点与 worker 的 PULL 端点必须一致（5551）。

### D5: 进程入口

`python -m hot_pulse.download_worker` 独立运行。后续由 `main.py` 以主子进程方式编排时，worker 提供 `run_download_worker()` 函数供调用。

## Risks / Trade-offs

- **[CDN 链接时效性]** → monitor 发现视频到 worker 消费之间有延迟，链接可能过期。缓解：monitor 每小时运行，worker 常驻即时消费，延迟通常在分钟级
- **[磁盘空间]** → 视频文件持续累积。缓解：当前阶段先不考虑自动清理，后续可加
- **[单进程瓶颈]** → 一次只下载一个视频。可接受：监控频率 59 分钟，新视频量有限
