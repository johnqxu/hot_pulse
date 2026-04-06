## 1. Worker 基座

- [x] 1.1 新增 `src/hot_pulse/worker_base.py`：定义 `WorkerHandler` 类型别名、`WorkerConfig` 基类（pull_endpoint, push_endpoint）、`run_worker()` 函数（初始化依赖、主循环、信号处理、资源清理）

## 2. 配置重构

- [x] 2.1 修改 `src/hot_pulse/config.py`：新增 `WorkerConfig` 基类，`DownloadWorkerConfig` 继承它

## 3. Download Worker 重构

- [x] 3.1 重构 `src/hot_pulse/download_worker.py`：提取 `handle_download(task, config)` handler，移除内联的公共逻辑，改用 `run_worker("download", handle_download)` 启动

## 4. 验证

- [x] 4.1 运行 download_worker（`python -m hot_pulse.download_worker`），配合 monitor 发送 Task，验证功能不变
