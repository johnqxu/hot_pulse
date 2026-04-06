## Context

当前 Hot Pulse 流水线由 5 个常驻 worker 进程 + 1 个临时 monitor 进程组成。用户需要手动逐个启动 worker，monitor 依赖外部 OpenClaw Cron 调度。缺少统一入口，运维成本高。

已实现模块均为独立 CLI 入口（`if __name__ == "__main__"`），worker 通过 `run_worker()` 基座封装，monitor 通过 `run_monitor()` 函数可被 import 调用。ZMQ PUSH/PULL 管道已配置好端口链。

## Goals / Non-Goals

**Goals:**
- 创建 main.py 作为一键启动入口，拉起所有 worker 子进程
- 内置 monitor 定时调度（07:00-22:00，每 59 分钟）
- worker 启动后等待 30 秒再开始 monitor
- 优雅关闭：SIGINT/SIGTERM 转发给所有子进程
- 各 worker 和 monitor 保持独立运行能力

**Non-Goals:**
- Worker 子进程崩溃自愈（后续实现）
- Worker 健康检查 / 心跳
- 配置热更新
- 进程监控仪表盘

## Decisions

### 1. 子进程管理：subprocess.Popen

**选择**：使用 `subprocess.Popen` 以 `python -m hot_pulse.xxx_worker` 方式启动 worker。

**理由**：
- 每个 worker 已有独立 CLI 入口，直接复用
- 进程隔离：worker 崩溃不影响主进程
- 无需引入额外依赖（如 multiprocessing、supervisor）
- 保留 worker 独立运行能力

**备选**：
- `multiprocessing.Process`：可直接调用函数，但共享进程空间，崩溃风险更高
- 第三方进程管理（supervisor、pm2）：引入额外依赖，过度工程化

### 2. Monitor 调度：主进程内直接调用 run_monitor()

**选择**：主进程 import `run_monitor()` 并在定时循环中直接调用。

**理由**：
- `run_monitor()` 已是独立函数，可直接 import
- 避免额外子进程管理
- 执行期间主进程阻塞，自然避免并发调度

**时间窗口逻辑**：
```
while not shutting_down:
    hour = datetime.now().hour
    if 7 <= hour < 22:
        run_monitor()
    sleep(59 * 60)
```

22:00-07:00 之间完全跳过 monitor 执行，主进程仅 sleep 等待。

### 3. Worker 启动顺序与延迟

**选择**：按管道顺序依次启动（download → extract_audio → transcribe → analyze → dingtalk_push），全部启动后等待 30 秒，再开始 monitor 调度。

**理由**：
- ZMQ PUSH/PULL 是无连接协议，push 端无需 pull 端在线即可发送
- 但 worker 启动时需要连接飞书、加载模型等初始化，30 秒延迟确保就绪
- 按顺序启动直观且日志清晰

### 4. 信号处理

**选择**：主进程捕获 SIGINT/SIGTERM，向所有子进程发送 terminate，等待退出。

**流程**：
1. 设置 signal handler，将 `shutting_down` 标记为 True
2. 在 monitor 循环中检查 `shutting_down`，为 True 时跳出循环
3. 遍历子进程列表，调用 `proc.terminate()`
4. 等待所有子进程退出（设超时，超时则 kill）

### 5. 配置

不新增配置项。Worker 启动命令硬编码为 `python -m hot_pulse.xxx_worker`，读取同一份 config.yaml。Monitor 的调度间隔和时间窗口使用 schedule.interval_minutes 配置（默认 59）。

## Risks / Trade-offs

- **[Worker 崩溃无自愈]** → 当前仅记录日志，后续实现自动重启
- **[30 秒延迟可能不够]** → 如果 worker 初始化耗时超过 30 秒（如模型加载），monitor 发送的任务可能无人消费。但 ZMQ 会缓冲消息，worker 就绪后会正常消费
- **[Windows 信号限制]** → Windows 上 SIGTERM 不可靠，需要使用 `proc.terminate()` 或 `CTRL_BREAK_EVENT`
- **[主进程与 monitor 同进程]** → 如果 run_monitor() 异常耗时过长，会阻塞信号检查。但 monitor 单次执行通常在几秒到几分钟内完成
