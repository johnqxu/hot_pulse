## ADDED Requirements

### Requirement: 主进程启动 worker 子进程

系统 SHALL 按管道顺序（download → extract_audio → transcribe → analyze → dingtalk_push）依次启动 5 个 worker 子进程。每个 worker 以 `python -m hot_pulse.xxx_worker` 方式启动为独立子进程。主进程 SHALL 记录每个子进程的 PID 和启动状态。主进程日志 SHALL 使用绿色 `[main]` 前缀标识。

#### Scenario: 正常启动所有 worker
- **WHEN** 执行 `python -m hot_pulse.main`
- **THEN** 系统按顺序启动 5 个 worker 子进程，每个启动成功后记录日志，包含 worker 类型和 PID
- **AND** 主进程日志前缀为绿色的 `[main]`，子进程日志各自使用对应颜色的 `[task_type]` 前缀

#### Scenario: worker 子进程启动失败
- **WHEN** 某个 worker 子进程启动时发生错误（如模块不存在）
- **THEN** 主进程 SHALL 记录错误日志，终止已启动的其他子进程，并退出

### Requirement: Monitor 定时调度

系统 SHALL 在所有 worker 子进程启动完成后等待 30 秒，然后进入 monitor 定时调度循环。调度间隔 SHALL 使用 `schedule.interval_minutes` 配置（默认 59 分钟）。每次调度 SHALL 直接调用 `run_monitor()` 函数。

#### Scenario: 时间窗口内执行 monitor
- **WHEN** 当前时间在 07:00-22:00 之间（含 07:00，不含 22:00）
- **THEN** 系统 SHALL 执行 `run_monitor()`，执行完成后等待 interval 分钟再进行下一次检查

#### Scenario: 时间窗口外跳过 monitor
- **WHEN** 当前时间在 22:00-07:00 之间
- **THEN** 系统 SHALL 跳过 monitor 执行，直接等待 interval 分钟后再检查

#### Scenario: monitor 执行异常
- **WHEN** `run_monitor()` 执行过程中抛出异常
- **THEN** 系统 SHALL 记录错误日志，继续等待下一次调度周期，不退出主进程

### Requirement: 优雅关闭

系统 SHALL 捕获 SIGINT 和 SIGTERM 信号，收到信号后 SHALL 停止 monitor 调度循环，向所有 worker 子进程发送 terminate 信号，并等待子进程退出。

#### Scenario: 收到 SIGINT 正常关闭
- **WHEN** 主进程收到 SIGINT 信号（如用户按 Ctrl+C）
- **THEN** 主进程 SHALL 停止 monitor 调度循环，依次向所有子进程发送 terminate，等待子进程退出（超时 10 秒），然后主进程退出

#### Scenario: 子进程未在超时内退出
- **WHEN** 某个子进程在收到 terminate 后 10 秒内未退出
- **THEN** 主进程 SHALL 强制 kill 该子进程并记录警告日志

### Requirement: 独立运行能力保留

各 worker 和 monitor SHALL 保持独立运行能力，可通过 `python -m hot_pulse.xxx_worker` 或 `python -m hot_pulse.monitor` 单独启动，不依赖 main.py。

#### Scenario: 独立启动 worker
- **WHEN** 用户直接执行 `python -m hot_pulse.download_worker`
- **THEN** worker SHALL 正常启动并运行，行为与 main.py 启动时一致

#### Scenario: 外部 cron 调度 monitor
- **WHEN** 外部调度器（OpenClaw Cron 或系统 cron）执行 `python -m hot_pulse.monitor`
- **THEN** monitor SHALL 正常执行一轮监控并退出，行为不受 main.py 影响
