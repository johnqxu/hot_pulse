## Purpose

Hot Pulse 主进程 — 单进程定时调度。启动时恢复中断任务，然后进入 monitor 定时循环。不再管理 worker 子进程（pipeline 直接函数调用串联 handler）。

## Requirements

### Requirement: Monitor 定时调度

系统 SHALL 启动后进入 monitor 定时调度循环。调度间隔 SHALL 使用 `schedule.interval_minutes` 配置（默认 59 分钟）。每次调度 SHALL 直接调用 `run_monitor()` 函数。

#### Scenario: 时间窗口内执行 monitor
- **WHEN** 当前时间在 07:00-24:00 之间（含 07:00，不含 24:00）
- **THEN** 系统 SHALL 执行 `run_monitor()`，执行完成后等待 interval 分钟再进行下一次检查

#### Scenario: 时间窗口外跳过 monitor
- **WHEN** 当前时间在 00:00-07:00 之间
- **THEN** 系统 SHALL 跳过 monitor 执行，直接等待 interval 分钟后再检查

#### Scenario: monitor 执行异常
- **WHEN** `run_monitor()` 执行过程中抛出异常
- **THEN** 系统 SHALL 记录错误日志，继续等待下一次调度周期，不退出主进程

### Requirement: 启动恢复

系统 SHALL 在进入调度循环前，调用 `pipeline.recover_interrupted_tasks(config)` 从飞书查询非终端状态任务并恢复执行。

#### Scenario: 有中断任务
- **WHEN** 启动时飞书表格中存在非终端状态记录（新视频、视频下载中、音频提取中、文字转写中、报告分析中、报告推送中、知识整理中）
- **THEN** 系统 SHALL 逐条恢复，根据 feishu_status 映射到对应 pipeline stage，调用 pipeline 从该 stage 继续执行

#### Scenario: 无中断任务
- **WHEN** 启动时飞书表格中无非终端状态记录
- **THEN** 系统 SHALL 记录日志并直接进入调度循环

### Requirement: 优雅关闭

系统 SHALL 捕获 SIGINT 和 SIGTERM 信号，收到信号后 SHALL 停止 monitor 调度循环并退出。

#### Scenario: 收到 SIGINT 正常关闭
- **WHEN** 主进程收到 SIGINT 信号（如用户按 Ctrl+C）
- **THEN** 主进程 SHALL 等待当前 pipeline 执行完成（如有），然后退出

#### Scenario: 调度等待中收到信号
- **WHEN** 主进程在调度间隔等待中收到关闭信号
- **THEN** 主进程 SHALL 立即退出等待循环并关闭

### Requirement: 独立运行能力

monitor 和 ingest SHALL 保持独立运行能力，可通过 `python -m hot_pulse.monitor` 或 `python -m hot_pulse ingest` 单独启动，不依赖 main.py。

#### Scenario: 外部 cron 调度 monitor
- **WHEN** 外部调度器（OpenClaw Cron 或系统 cron）执行 `python -m hot_pulse.monitor`
- **THEN** monitor SHALL 正常执行一轮监控并退出，行为不受 main.py 影响

#### Scenario: 手动 ingest
- **WHEN** 用户执行 `python -m hot_pulse ingest --type video --platform bilibili --url ...`
- **THEN** ingest SHALL 解析元信息、创建飞书记录、执行 pipeline 并退出
