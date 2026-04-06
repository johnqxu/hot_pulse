## MODIFIED Requirements

### Requirement: run_worker 通用主循环
系统 SHALL 提供 `run_worker()` 函数，封装所有 worker 共有的初始化和主循环逻辑，通过 handler 回调执行具体业务，主循环处理 ZMQ 接收超时以支持 Windows 下优雅关闭。

#### Scenario: 成功处理单个任务
- **WHEN** 调用 `run_worker(task_type, handler, config_path)`
- **THEN** 系统 SHALL 加载配置，初始化 FeishuClient、TaskManager、ZmqConsumer（pull）、ZmqPublisher（push）
- **AND** 进入主循环，从 ZMQ PULL 接收 Task
- **AND** 若 task_type 匹配，调用 `tm.start(task)`
- **AND** 调用 `handler(task, config)` 获取 outputs dict
- **AND** 调用 `tm.finish(task, outputs)`
- **AND** 调用 `tm.build_next(task)`，若非 None 则通过 ZMQ PUSH 发送

#### Scenario: handler 抛出异常
- **WHEN** handler 执行过程中抛出异常
- **THEN** 系统 SHALL 调用 `tm.fail(task, error_message)`
- **AND** 继续处理下一个 Task

#### Scenario: 收到非目标类型的 Task
- **WHEN** 收到的 Task 的 task_type 与 run_worker 注册的 task_type 不匹配
- **THEN** 系统 SHALL 记录警告日志并跳过该 Task

#### Scenario: ZMQ 接收超时
- **WHEN** recv_task() 因超时抛出 zmq.Again
- **THEN** 系统 SHALL 检查 shutting_down 标志
- **AND** 若未关闭则继续循环等待
- **AND** 若正在关闭则退出循环

#### Scenario: Worker 优雅关闭
- **WHEN** worker 进程收到 SIGINT 或 SIGTERM 信号
- **THEN** 系统 SHALL 设置关闭标志，当前 recv_task 最多等 1 秒后超时返回
- **AND** 在 finally 中关闭 ZMQ Consumer、Publisher 和 FeishuClient
