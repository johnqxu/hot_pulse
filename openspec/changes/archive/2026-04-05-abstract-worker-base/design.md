## Context

当前 download_worker.py 包含约 70 行代码，其中约 55 行是所有 worker 共有的公共逻辑：配置加载、FeishuClient + TaskManager 初始化、ZMQ Consumer/Publisher 创建、SIGINT/SIGTERM 信号处理、while 循环（recv → type 过滤 → start → 业务 → finish → build_next → send）、finally 资源清理。

后续 extract_audio、transcribe、analyze 三个 worker 需要完全相同的骨架，仅业务处理函数不同。

关键约束：
- 每个 worker 是独立进程，通过 ZMQ PUSH/PULL 通信
- handler 签名统一：接收 Task + AppConfig，返回 outputs dict
- 项目风格偏好函数式，不使用类继承层次

## Goals / Non-Goals

**Goals:**
- 提供 `run_worker()` 函数封装所有 worker 共有的初始化、主循环、清理逻辑
- 定义 `WorkerHandler` 类型协议：`(Task, AppConfig) -> dict`
- 重构 download_worker 使用 `run_worker()` + handler
- 抽象 `WorkerConfig` 基类（pull_endpoint, push_endpoint），各 worker 配置继承它

**Non-Goals:**
- 不实现多 worker 并发/线程池
- 不实现任务优先级或调度
- 不修改 Task、TaskManager 的接口
- 不修改 monitor 的任何行为

## Decisions

### D1: 函数式 run_worker 而非基类继承

选择 `run_worker(task_type, handler, config_path)` 函数签名，而非 BaseWorker 抽象基类。

理由：
- 每个 worker 的"个性"就是一个函数，用类包装一个函数是多余的
- Python 风格偏好组合和 callable
- 未来各 worker 文件只需定义 handler + `__main__` 入口，极其简洁

```python
# worker_base.py
WorkerHandler = Callable[[Task, AppConfig], dict]

def run_worker(
    task_type: str,
    handler: WorkerHandler,
    config_path: str = "config.yaml",
) -> None: ...
```

### D2: WorkerConfig 基类

```python
class WorkerConfig(BaseModel):
    pull_endpoint: str
    push_endpoint: str

class DownloadWorkerConfig(WorkerConfig):
    download_dir: str = r"D:\batch\video"
```

各 worker 配置继承 WorkerConfig，添加各自特有字段。pull_endpoint 和 push_endpoint 为必填，不再有默认值——避免端口冲突的隐患。

### D3: 异常映射约定

handler 抛异常 → `run_worker` 捕获 → `TaskManager.fail()`。handler 正常返回 dict → `TaskManager.finish()`。这个约定已在 download_worker 中建立，直接提升为 `run_worker` 的契约。

### D4: handler 签名接收 AppConfig 而非具体 WorkerConfig

handler 签名为 `(task: Task, config: AppConfig) -> dict`，而非 `(task, download_config)`。

理由：
- handler 可能需要访问公共配置（如飞书配置）
- 保持 run_worker 的统一签名，不因 worker 不同而变
- 各 handler 自行从 config 中提取自己需要的配置段

## Risks / Trade-offs

- **[handler 接口过于简单]** → 如果未来某个 worker 需要在 handler 内发送额外 ZMQ 消息，当前签名不支持。缓解：目前所有 worker 都是单进单出模式，YAGNI
- **[配置基类继承层次]** → WorkerConfig → DownloadWorkerConfig 是一层继承。如果后续 worker 没有额外配置字段，继承显得多余。缓解：继承只有一层，复杂度可控
