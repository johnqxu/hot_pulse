## Why

监控阶段（monitor）已能发现新视频并通过 ZMQ 发送 download 类型的 Task，但目前没有消费者接收并执行下载。download worker 是流水线的第一个常驻进程，需要从 ZMQ PULL 拉取任务、下载视频文件、更新飞书记录，并将任务传递给下一阶段（extract_audio）。

## What Changes

- 新增 `src/hot_pulse/download_worker.py`：常驻进程，循环从 ZMQ PULL 接收 Task，执行视频下载，通过 TaskManager 管理生命周期
- 新增下载逻辑：使用 httpx 流式下载，遍历 play_urls 列表按顺序尝试，首个成功即返回
- 下载文件存储到 `D:\batch\video\{video_id}.mp4`
- 下载完成后通过 ZMQ PUSH 发送下一阶段 Task（extract_audio）给下游消费者
- 修改 `config.yaml`：新增 download_worker 配置段（ZMQ 端口、下载目录）

## Capabilities

### New Capabilities
- `download-worker`: 视频下载 worker，从 ZMQ 接收 download 类型 Task，执行视频下载，更新飞书记录，向下游发送 extract_audio 类型 Task

### Modified Capabilities
- `config-management`: 新增 download_worker 配置段（ZMQ pull/push 端点、下载目录）
- `zeromq-publisher`: 新增 send_task 用法说明（download worker 既做消费者也做生产者）

## Impact

- 新增文件：`src/hot_pulse/download_worker.py`
- 修改文件：`src/hot_pulse/config.py`（新增 DownloadWorkerConfig）、`config.yaml`
- 依赖：httpx（已有，用于流式下载）
- 文件系统：在 `D:\batch\video\` 目录下创建视频文件
