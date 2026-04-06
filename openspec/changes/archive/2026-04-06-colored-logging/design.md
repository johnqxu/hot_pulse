## Context

当前 loguru 日志格式为 `{time:HH:mm:ss} | {level} | {message}`，主进程和所有 worker 子进程使用相同的格式和颜色，在终端混在一起时无法区分。

## Goals / Non-Goals

**Goals:**
- 主进程和每个 worker 子进程使用不同的日志颜色
- 通过日志中的进程标识前缀（如 `[main]`、`[download]`）和颜色区分来源
- 仅影响终端 stderr 输出

**Non-Goals:**
- 不修改文件日志格式
- 不引入额外依赖

## Decisions

### 1. 颜色方案

使用 loguru 内置的颜色标签，在格式字符串中嵌入 `<tag>` 样式标记：

| 进程 | 颜色 | 标识前缀 |
|------|------|----------|
| main | 绿色 | `[main]` |
| download | 青色 | `[download]` |
| extract_audio | 黄色 | `[extract_audio]` |
| transcribe | 蓝色 | `[transcribe]` |
| analyze | 洋红 | `[analyze]` |
| dingtalk_push | 红色 | `[dingtalk]` |

### 2. 实现方式

**worker_base.py**：在 `run_worker()` 中根据 `task_type` 选择颜色，在 `logger.add()` 的 format 中嵌入颜色标签和进程名前缀。

**main.py**：在 `logger.add()` 的 format 中使用绿色标记和 `[main]` 前缀。

格式示例：
```
HH:mm:ss | level | <green>[main]</green> message
HH:mm:ss | level | <cyan>[download]</cyan> message
```

### 3. loguru colorize

loguru 默认在检测到终端时自动启用 colorize，`<tag>` 颜色标记会被渲染为 ANSI 颜色码。无需额外配置。

## Risks / Trade-offs

- **[Windows 终端兼容性]** → Windows Terminal 和 PowerShell 7 支持 ANSI 颜色。旧版 cmd 可能不显示颜色，但不影响功能
- **[日志前缀增加长度]** → 前缀很短（`[main]` 约 7 字符），影响可忽略
