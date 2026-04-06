## MODIFIED Requirements

### Requirement: 主进程启动 worker 子进程

系统 SHALL 按管道顺序启动 5 个 worker 子进程。主进程日志 SHALL 使用绿色 `[main]` 前缀标识。

#### Scenario: 正常启动所有 worker
- **WHEN** 执行 `python -m hot_pulse.main`
- **THEN** 主进程日志前缀为绿色的 `[main]`，子进程日志各自使用对应颜色的 `[task_type]` 前缀
