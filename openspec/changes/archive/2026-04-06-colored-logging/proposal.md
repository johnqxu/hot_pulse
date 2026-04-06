## Why

main.py 启动后，主进程（monitor 调度）和 5 个 worker 子进程的日志混在一起，难以区分来源。需要为不同进程分配不同颜色的日志前缀，方便快速定位问题。

## What Changes

- 修改 `main.py`：主进程日志使用特定颜色标识
- 修改 `worker_base.py`：worker 子进程日志使用进程对应的颜色标识
- 利用 loguru 的 `colorize` 功能，在日志格式中加入颜色标记

## Capabilities

### New Capabilities
（无新增能力）

### Modified Capabilities
- `main-orchestrator`: 主进程日志添加颜色标识
- `worker-base`: worker 子进程日志添加颜色标识

## Impact

- 修改文件：`src/hot_pulse/main.py`、`src/hot_pulse/worker_base.py`
- 不影响日志内容，仅影响终端显示颜色
- 仅对 stderr 输出生效，文件日志不受影响
