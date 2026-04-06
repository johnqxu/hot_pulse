## Context

当前 `TaskManager.start()` 仅更新飞书的开始时间字段（如"视频下载开始时间"），不更新"状态"字段。飞书"状态"字段在 `finish()` 时写入 `finish_status`，`fail()` 时统一写入"失败"。缺少任务执行中的状态表示。

用户要求统一状态命名规范：除"新视频"外，所有状态遵循 **交付物+动词+状态** 格式。

完整状态链：

```
"新视频" ──[start]──▶ "视频下载中" ──[finish]──▶ "视频下载完成"
                       │
                       └─[fail]──▶ "视频下载失败"

"视频下载完成" ──[start]──▶ "音频提取中" ──[finish]──▶ "音频提取完成"
                               │
                               └─[fail]──▶ "音频提取失败"

"音频提取完成" ──[start]──▶ "文字转写中" ──[finish]──▶ "文字转写完成"
                               │
                               └─[fail]──▶ "文字转写失败"

"文字转写完成" ──[start]──▶ "报告分析中" ──[finish]──▶ "报告分析完成"
                               │
                               └─[fail]──▶ "报告分析失败"
```

## Goals / Non-Goals

**Goals:**
- StageConfig 新增 `running_status` 和 `fail_status` 字段
- `TaskManager.start()` 将 `running_status` 写入飞书"状态"字段
- `TaskManager.fail()` 将 `fail_status` 写入飞书"状态"字段（替代统一"失败"）
- 统一 analyze 阶段的 `finish_status` 从"分析完成"改为"报告分析完成"

**Non-Goals:**
- 不修改飞书表格结构（仅新增单选值）
- 不实现进度百分比等细分状态

## Decisions

### D1: 状态命名规范

统一格式：**交付物+动词+状态**（"新视频"除外）

| 阶段 | init_status | running_status | finish_status | fail_status |
|---|---|---|---|---|
| download | 新视频 | 视频下载中 | 视频下载完成 | 视频下载失败 |
| extract_audio | 视频下载完成 | 音频提取中 | 音频提取完成 | 音频提取失败 |
| transcribe | 音频提取完成 | 文字转写中 | 文字转写完成 | 文字转写失败 |
| analyze | 文字转写完成 | 报告分析中 | 报告分析完成 | 报告分析失败 |

### D2: StageConfig 新增字段

在 StageConfig 中新增 `running_status` 和 `fail_status`：

```python
@dataclass(frozen=True)
class StageConfig:
    init_status: str
    running_status: str
    finish_status: str
    fail_status: str
    start_field: str
    end_field: str
    ...
```

### D3: start() 和 fail() 写入飞书

- `TaskManager.start()`: 同时写入开始时间和"状态"字段（设为 `running_status`）
- `TaskManager.fail()`: 写入 `fail_status` 到"状态"字段（替代硬编码的"失败"）

## Risks / Trade-offs

- **[飞书单选值维护]** → 每个阶段需要新增 running_status 和 fail_status 两个单选值。可接受：共 8 个新值
- **[analyze 的 finish_status 变更]** → "分析完成"改为"报告分析完成"，需在飞书表格中新增该选项。旧的"分析完成"单选值可保留不影响
