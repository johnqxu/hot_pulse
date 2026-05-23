## Context

`TaskManager.build_next` 当前直接从 `STAGE_MAPPING[task.task_type].next_type` 获取下一阶段，不做任何条件判断。需要在此处增加 source 检查。

## Decisions

### 1. build_next 分流

```python
def build_next(self, task: Task) -> Task | None:
    cfg = STAGE_MAPPING.get(task.task_type)
    if cfg is None:
        return None

    # transcribe 阶段根据 source 分流
    next_type = cfg.next_type
    if task.task_type == "transcribe" and task.source == "manual":
        next_type = "knowledge"

    if next_type is None:
        return None
    ...
```

### 2. STAGE_MAPPING 新增 knowledge

```python
"knowledge": StageConfig(
    init_status="文字转写完成",
    running_status="知识整理中",
    finish_status="知识整理完成",
    fail_status="知识整理失败",
    start_field="内容分析开始时间",
    end_field="内容分析结束时间",
    output_map={"obsidian_note": "分析报告地址"},
    next_type=None,
    next_input_map={"text_file": "text_file"},
),
```

### 3. 飞书字段复用

Knowledge 阶段暂时复用 analyze 的飞书字段（`内容分析开始时间`/`内容分析结束时间`/`分析报告地址`），先跑通分流路由。Proposal 4 再做专属字段。
