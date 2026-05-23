## Context

当前 Task 模型标识字段为 `task_type`（`download | extract_audio | transcribe | analyze | dingtalk_push`），控制阶段路由。需要在 `task_type` 维度之外增加 `source` 维度，标记任务来源（`"subscription"` = TikTok 定时监控，`"manual"` = 用户手动提交），为后续 Proposal 3（transcribe 根据 source 分流）提供基础。

## Goals / Non-Goals

**Goals:**
- `Task` 模型新增 `source: str = "subscription"` 字段
- `monitor.py` 中构造 Task 时显式传 `source="subscription"`
- 下游 ZMQ 序列化/反序列化自动兼容

**Non-Goals:**
- 不基于 source 做任何路由逻辑（留给 Proposal 3）
- 不修改 worker_base / task_manager / 任何现有 worker

## Decisions

### 1. 字段设计

放置在"源信息"区域，与 `video_id`、`creator` 等并列：

```python
class Task(BaseModel):
    # 身份标识
    task_id: str
    task_type: str

    # 源信息
    video_id: str
    creator: str
    title: str
    platform: str = "抖音"
    source: str = "subscription"      # ← 新增
    feishu_record_id: str = ""
```

**为什么不用枚举？** 两个字符串 `"subscription"` / `"manual"` 足够简单，枚举增加 import 开销且 ZMQ 反序列化时需额外转换。后续如有第 3 种 source 再重构。

### 2. 默认值选择

- `"subscription"` 作为默认值 → 所有已有代码（包括 `ingest.py` 之外的任何地方）构造 Task 时无需显式传递
- 只有 `ingest.py`（Proposal 2）需要显式传 `source="manual"`
- 这保证了严格的向后兼容

### 3. 影响范围

```
task.py  ── 加 1 行
monitor.py  _send_zmq_task ── 加 source="subscription"（显式，自文档化）

以下完全不动：
  worker_base.py, task_manager.py, download_worker.py,
  extract_audio_worker.py, transcribe_worker.py,
  analyze_worker.py, dingtalk_worker.py,
  feishu.py, zmq_client.py
```

### 4. ZMQ 兼容性

pydantic `BaseModel` 的 `model_dump_json()` / `model_validate_json()` 自动处理新增字段。下游 worker 收到的 Task JSON 中会多一个 `"source": "subscription"` 键，worker 不使用则忽略。

## Risks / Trade-offs

- **无风险**: 改动极小，仅新增一个带默认值的字段，编译时即可验证
