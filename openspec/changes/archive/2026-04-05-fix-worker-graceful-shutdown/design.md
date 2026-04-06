## Context

当前 `ZmqConsumer.recv_task()` 调用 `self._socket.recv()`（无超时）。在 Windows 上，Python 的 `signal.signal(SIGINT, handler)` 只能在 Python 字节码之间执行，无法中断 ZMQ C 扩展中的阻塞 recv。因此 Ctrl+C 无法被处理，进程卡死在 recv 调用上。

## Goals / Non-Goals

**Goals:**
- 修复 Windows 下 Ctrl+C 无法优雅关闭 worker 的问题
- recv_task 周期性返回控制权，让信号处理器有机会执行

**Non-Goals:**
- 不修改 ZmqPublisher
- 不修改 Task 或 TaskManager
- 不引入 polling/event loop 框架

## Decisions

### D1: RCVTIMEO 超时方案

在 ZMQ PULL socket 上设置 `RCVTIMEO = 1000`（1 秒）。`recv()` 超时后抛出 `zmq.Again`，`run_worker` 捕获后检查 shutting_down 标志。

选择理由：
- 零外部依赖，ZMQ 原生支持
- 1 秒响应时间对用户可接受（Ctrl+C 后最多等 1 秒）
- 不改变 recv 的使用模式

替代方案：
- `zmq.Poller` + timeout：更灵活但代码更复杂，当前只有一个 socket
- `socket.close()` 从信号处理器中关闭：C 层面的线程安全问题

### D2: zmq.Again 不暴露给调用方

`recv_task()` 超时后直接抛出 `zmq.Again`，`run_worker` 捕获处理。调用方无需感知超时机制。

## Risks / Trade-offs

- **[1 秒延迟]** → Ctrl+C 后最多等 1 秒才退出。可接受：用户感知为"立即"
- **[频繁 try/except]** → 每秒一次 zmq.Again 捕获。性能影响可忽略：仅一次异常创建+捕获
