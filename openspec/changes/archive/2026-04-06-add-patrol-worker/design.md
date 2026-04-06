## Context

Worker 进程在执行任务时可能因崩溃、OOM、手动 kill 等原因异常退出。此时飞书表格中该任务停留在 running_status（如"视频下载中"）或 fail_status（如"视频下载失败"），但没有任何 worker 会重新处理这些记录——当前 worker 启动恢复只查询 init_status。

## Goals / Non-Goals

**Goals:**
- 定时巡检飞书表格，自动发现僵尸任务（running > 90min）和失败任务
- 回退飞书状态到该阶段的 init_status
- 通过 ZMQ PUSH 通知对应 worker 重新处理
- 集成到 main.py 统一启动

**Non-Goals:**
- 重试次数上限（技术债务，后续实现）
- Worker 健康检查 / 心跳
- 任务优先级调整

## Decisions

### 1. 巡检方式：独立 worker 进程

**选择**：作为独立 worker 进程运行，类似 monitor 的模式。

**理由**：
- 复用现有 worker 基座和 main.py 子进程管理
- 独立进程，崩溃不影响其他 worker
- 定时逻辑简单，不需要外部调度器

### 2. 状态反向映射

巡检需要从飞书的 running_status / fail_status 反查到 task_type 和 init_status。通过构建反向映射表实现：

```python
# 从 STAGE_MAPPING 自动构建
STAGE_REVERSE: dict[str, tuple[str, str]] = {
    # running_status/fail_status → (task_type, init_status)
    "视频下载中":   ("download", "新视频"),
    "视频下载失败": ("download", "新视频"),
    "音频提取中":   ("extract_audio", "视频下载完成"),
    "音频提取失败": ("extract_audio", "视频下载完成"),
    ...
}
```

### 3. 僵尸检测：基于时间戳

每条飞书记录有 `start_field`（如"视频下载开始时间"），值为毫秒时间戳。巡检时计算 `now - start_time`，超过阈值（默认 90 分钟）即判定为僵尸。

fail_status 记录无需检查时间，直接回退。

### 4. ZMQ 路由

巡检 worker 需要向不同 worker 的 pull_endpoint 推送任务。从 config 中获取各 worker 的 pull_endpoint：

```python
ROUTES = {
    "download": config.download_worker.pull_endpoint,       # 5551
    "extract_audio": config.extract_audio_worker.pull_endpoint,  # 5552
    "transcribe": config.transcribe_worker.pull_endpoint,        # 5553
    "analyze": config.analyze_worker.pull_endpoint,              # 5554
    "dingtalk_push": config.dingtalk_worker.pull_endpoint,       # 5555
}
```

为每个 endpoint 创建 ZMQ PUSH socket，按 task_type 路由发送。

### 5. 飞书查询策略

需要查询所有记录并逐条过滤。飞书 API 不支持 "状态 != 完成" 这种过滤，所以：
- 查询全部记录（分页）
- 内存中过滤出 running_status 和 fail_status 的记录

或者，为每种 running/fail 状态单独查询（利用飞书的 "状态 is xxx" 过滤），减少无效数据传输。

**选择后者**——按状态逐个查询，更高效。

### 6. 飞书回退与 ZMQ 通知的顺序

先回退飞书状态，再发 ZMQ。如果 ZMQ 发送失败，worker 启动恢复机制兜底（会在下次重启时捡起 init_status 记录）。

### 7. 配置

```yaml
patrol_worker:
  interval_minutes: 60      # 巡检间隔
  zombie_threshold_minutes: 90  # 僵尸判定阈值
```

## Risks / Trade-offs

- **[无重试上限]** → 反复失败的任务会无限循环。后续需加重试次数字段 → 记为技术债务
- **[飞书查询量]** → 每次巡检按 10 种状态（5 running + 5 fail）分别查询，每次 1 个 API 调用，共 10 次。可接受
- **[ZMQ 多 socket]** → 巡检 worker 持有 5 个 PUSH socket，资源占用小，可接受
- **[并发安全]** → 如果 worker 正好在处理某条记录时巡检将其回退，可能出现重复处理。但各 handler 应具备幂等性（文件已存在则跳过），影响可控
