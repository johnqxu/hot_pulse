## Why

当前各 worker 需要手动逐个启动，monitor 依赖外部 OpenClaw Cron 调度。缺少一个统一入口来一键拉起整个流水线。需要 main.py 作为主进程编排器，管理所有 worker 子进程的生命周期，并内置 monitor 定时调度，同时保留各组件独立运行的能力。

## What Changes

- 新增 `src/hot_pulse/main.py` 主进程编排器：
  - 按管道顺序启动 5 个 worker 子进程（download → extract_audio → transcribe → analyze → dingtalk_push）
  - 等待 30 秒确保 worker 就绪后，启动 monitor 定时调度
  - 内置时间窗口控制：仅在 07:00-22:00 之间执行 monitor，每 59 分钟一次
  - 22:00-07:00 完全不调度 monitor
  - 统一信号处理：SIGINT/SIGTERM 时优雅关闭所有子进程
- 各 worker 和 monitor 保持独立运行能力不变（`python -m hot_pulse.xxx_worker`、`python -m hot_pulse.monitor`）
- monitor 既可由 main.py 内置调度运行，也可由外部 cron / OpenClaw 独立调度

## Capabilities

### New Capabilities
- `main-orchestrator`: 主进程编排器，负责 worker 子进程管理和 monitor 定时调度

### Modified Capabilities
（无需修改现有 spec，各 worker 和 monitor 的行为不变）

## Impact

- 新增文件：`src/hot_pulse/main.py`
- 不影响现有 worker_base.py、monitor.py 及各 worker 的代码
- 部署方式变更：从"手动启动多个进程 + 外部 cron"变为"可选一键启动 main.py"
