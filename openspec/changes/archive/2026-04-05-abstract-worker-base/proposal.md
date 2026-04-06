## Why

download_worker 中大量代码是所有 worker 共有的公共逻辑（配置加载、依赖创建、ZMQ 收发、主循环、信号处理、资源清理），实际业务逻辑仅占一个函数调用。后续 extract_audio、transcribe、analyze 三个 worker 将重复完全相同的骨架代码。需要在当前只有一个 worker 的情况下提前抽象，避免 4 份几乎一样的代码。

## What Changes

- 新增 `src/hot_pulse/worker_base.py`：提供 `run_worker()` 函数，封装所有 worker 共有的初始化和主循环逻辑
- 定义 `WorkerHandler` 协议（`Callable[[Task, AppConfig], dict]`）：每个 worker 只需提供一个 handler 函数
- 重构 `src/hot_pulse/download_worker.py`：移除公共骨架代码，仅保留 `_download_video()` 和 `handle_download()` handler，通过 `run_worker("download", handle_download)` 启动
- 修改配置结构：新增 `WorkerConfig` 基类（pull_endpoint + push_endpoint），各阶段 worker 配置继承它

## Capabilities

### New Capabilities
- `worker-base`: 通用 worker 基座，提供 `run_worker()` 函数封装 ZMQ 收发、TaskManager 生命周期、信号处理、资源清理等公共逻辑

### Modified Capabilities
- `download-worker`: 重构为基于 worker-base 的 handler 模式，移除内联的公共逻辑
- `config-management`: 新增 `WorkerConfig` 基类，重构 `DownloadWorkerConfig` 继承它

## Impact

- 新增文件：`src/hot_pulse/worker_base.py`
- 修改文件：`src/hot_pulse/download_worker.py`（大幅简化）、`src/hot_pulse/config.py`
- 无外部依赖变化
- download_worker 的行为不变，纯内部重构
