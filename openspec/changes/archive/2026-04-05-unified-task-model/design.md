## Context

当前 monitor 产出的 ZMQ 消息是临时构造的 dict，后续阶段（download/extract_audio/transcribe/analyze）需要以相同模式运行：接收任务 → 更新飞书开始时间 → 执行处理 → 更新飞书完成时间和产出物 → 推送下一阶段。需要统一的任务抽象避免重复实现。

关键约束：
- Task 不持久化，是纯内存消息信封
- 飞书多维表格是唯一持久化真相来源
- ZMQ PUSH/PULL 是跨进程通信机制
- 每个 stage 是独立进程

## Goals / Non-Goals

**Goals:**
- 定义 Task Pydantic Model，作为流水线统一消息格式
- 实现 TaskManager，封装 start/finish/fail 时的飞书同步和日志
- 定义阶段配置映射（stage → 飞书字段映射）
- monitor 产出的 ZMQ 消息改为 Task 格式
- 为后续阶段 worker 提供可复用的基础设施

**Non-Goals:**
- 不实现任何具体的阶段 worker（download/extract_audio/transcribe/analyze）
- 不实现任务持久化、恢复、重试机制
- 不修改飞书表格结构

## Decisions

### D1: Task 是 Pydantic Model

```python
class Task(BaseModel):
    task_id: str
    task_type: str               # "download" | "extract_audio" | "transcribe" | "analyze"
    video_id: str
    creator: str
    title: str
    platform: str = "抖音"
    feishu_record_id: str = ""   # monitor 写入飞书后回填
    inputs: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    status: str = "pending"      # pending | running | done | failed
    error: str = ""
    created_at: str = ""
    updated_at: str = ""
```

选择 Pydantic 而非 dataclass：自带 JSON 序列化/反序列化（`model_dump()` / `model_validate()`）、类型校验。

### D2: 阶段配置映射

每个 task_type 声明自己对应的飞书字段：

```python
STAGE_MAPPING = {
    "download": StageConfig(
        start_field="视频下载开始时间",
        end_field="视频下载完成时间",
        output_map={"video_file": "视频文件地址"},
        next_type="extract_audio",
        next_input_map={"video_file": "video_file"},
    ),
    "extract_audio": StageConfig(
        start_field="音频提取开始时间",
        end_field="音频提取完成时间",
        output_map={"audio_file": "音频文件地址"},
        next_type="transcribe",
        next_input_map={"audio_file": "audio_file"},
    ),
    "transcribe": StageConfig(
        start_field="文字转写开始时间",
        end_field="文字转写完成时间",
        output_map={"text_file": "文字文件地址"},
        next_type="analyze",
        next_input_map={"text_file": "text_file"},
    ),
    "analyze": StageConfig(
        start_field="内容分析开始时间",
        end_field="内容分析结束时间",
        output_map={"report_file": "分析报告地址"},
        next_type=None,
    ),
}
```

`next_input_map` 定义如何将当前 outputs 映射为下一阶段的 inputs。例如 download 的 output `video_file` 映射为 extract_audio 的 input `video_file`。

### D3: TaskManager 能力层

```python
class TaskManager:
    def start(self, task: Task) -> Task: ...
    def finish(self, task: Task, outputs: dict) -> Task: ...
    def fail(self, task: Task, error: str) -> Task: ...
    def build_next(self, task: Task) -> Task | None: ...
```

- `start()`: 更新 task.status="running" → 飞书 PATCH 开始时间 + 状态 → 日志
- `finish()`: 更新 task.status="done" → 飞书 PATCH 结束时间 + outputs → 日志
- `fail()`: 更新 task.status="failed" → 飞书 PATCH 错误状态 → 日志
- `build_next()`: 基于 STAGE_MAPPING 构造下一阶段 Task（outputs → inputs）

### D4: feishu_record_id 的流转

```
monitor 写入飞书 → 飞书返回 record_id → 填入 Task → ZMQ 发出
                                                     ↓
download_worker 收到 Task（已含 record_id）→ 用它更新飞书记录
```

需修改 `feishu.py` 的 `create_records` 返回 record_id 列表。

### D5: 项目结构

```
src/hot_pulse/
├── task.py           # 新增：Task Pydantic Model
├── task_manager.py   # 新增：TaskManager + StageConfig
├── models.py         # 保留：飞书 VideoRecord（monitor 内部使用）
├── monitor.py        # 修改：ZMQ 消息改为 Task 格式
├── feishu.py         # 修改：create_records 返回 record_id，新增 update_record
├── zmq_client.py     # 修改：支持发送/接收 Task 对象
```

## Risks / Trade-offs

- **[飞书表格字段需与 STAGE_MAPPING 一致]** → 飞书字段如有变动，需同步更新 STAGE_MAPPING。缓解：STAGE_MAPPING 是唯一配置点
- **[record_id 获取失败]** → create_records 可能部分成功。缓解：逐条写入并捕获每条的 record_id
- **[Task 无持久化]** → 进程崩溃后无法从 Task 恢复。可接受：飞书表格是兜底，后续可基于飞书状态补偿
