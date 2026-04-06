## Context

当前 run_worker() 启动后直接进入 ZMQ recv 主循环。飞书记录的"状态"字段（type=3 单选）仅在 monitor 创建时设为"新视频"、TaskManager.fail() 时设为"失败"，TaskManager.finish() 不更新状态。导致：记录永远停留在"新视频"，无法通过状态查询判断一条记录处于哪个阶段。

关键约束：
- 飞书表格已有"状态"字段（type=3 单选），当前可选值："新视频"、"失败"
- 飞书 search API 支持 field_name + operator + value 的条件过滤
- 每个阶段的 init_status 和 finish_status 在 STAGE_MAPPING 中静态配置

## Goals / Non-Goals

**Goals:**
- StageConfig 新增 init_status 和 finish_status，定义状态链
- TaskManager.finish() 将 finish_status 写入飞书"状态"字段
- FeishuClient 新增按状态查询记录的方法
- run_worker() 启动时从飞书加载历史任务并处理

**Non-Goals:**
- 不实现僵尸任务重试检测（重复执行 handler 即可）
- 不实现幂等性检测（如检查文件是否已存在）
- 不修改飞书表格结构（仅新增单选值）

## Decisions

### D1: 状态链设计

```
"新视频" ──[download]──▶ "视频下载完成" ──[extract_audio]──▶ "音频提取完成" ──[transcribe]──▶ "文字转写完成" ──[analyze]──▶ "分析完成"
                                                                                                              │
任何阶段 fail() ─────────────────────────────────────────────────────────────────────────────────────────────▶ "失败"
```

StageConfig 配置：

```python
"download":      StageConfig(init_status="新视频",       finish_status="视频下载完成", ...)
"extract_audio": StageConfig(init_status="视频下载完成",  finish_status="音频提取完成", ...)
"transcribe":    StageConfig(init_status="音频提取完成",  finish_status="文字转写完成", ...)
"analyze":       StageConfig(init_status="文字转写完成",  finish_status="报告分析完成", ...)
```

### D2: FeishuClient.query_records_by_status()

使用飞书 records/search API，按"状态"字段过滤，返回的记录构造为 Task 列表。

需要从飞书记录中提取：
- record_id → task.feishu_record_id
- 视频ID → task.video_id
- 博主 → task.creator
- 任务名 → task.title
- 视频链接 → task.inputs["play_urls"]（JSON 解析）
- 平台 → task.platform

各阶段还需要额外的 inputs（如 extract_audio 需要 video_file），这些信息不在飞书表格中（只有文件地址），但可以从飞书字段的上一阶段 output_map 反向读取。

### D3: run_worker() 启动恢复流程

```python
def run_worker(task_type, handler, config_path):
    ...
    # 1. 启动时从飞书加载历史任务
    cfg = STAGE_MAPPING[task_type]
    pending_tasks = feishu.query_records_by_status(cfg.init_status, task_type)
    for task in pending_tasks:
        handler(task, config)  # 通过 tm 管理

    # 2. 然后进入 ZMQ 主循环
    while not shutting_down:
        task = consumer.recv_task()
        ...
```

历史任务不走 ZMQ 发送（不需要通知下游），而是由 finish() → build_next() 自然驱动下一阶段。

### D4: 飞书记录到 Task 的映射

query_records_by_status 返回的飞书记录需要构造为 Task 对象。各阶段的 inputs 来源不同：

- download: inputs = {"play_urls": JSON解析(视频链接)}
- extract_audio: inputs = {"video_file": 视频文件地址字段的值}
- transcribe: inputs = {"audio_file": 音频文件地址字段的值}
- analyze: inputs = {"text_file": 文字文件地址字段的值}

这可以通过 StageConfig 的上一阶段 output_map 反向推导，或者在 StageConfig 中新增 `input_map`（从飞书字段名到 Task input key 的映射）。

为简洁起见，直接在 query 方法中根据 task_type 从飞书记录提取对应字段。

## Risks / Trade-offs

- **[重复执行]** → worker 崩溃后重启，handler 可能对同一任务重复执行（如重新下载文件）。可接受：第一版不优化，后续可加幂等检测
- **[飞书查询性能]** → 随着记录增多，按状态查询可能变慢。缓解：当前数据量小（< 1000 条），飞书 search API 有分页支持
- **[状态不一致窗口]** → finish_status 写入成功但 build_next 发送失败时，下一阶段 worker 可通过启动恢复补上。这正是本方案要解决的问题
