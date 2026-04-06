## Purpose

通用 worker 基座，封装所有 worker 共有的初始化、主循环、信号处理和资源清理逻辑。

## Requirements

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

#### Scenario: 启动时恢复历史任务
- **WHEN** run_worker 启动后进入 ZMQ 主循环之前
- **THEN** 系统 SHALL 根据当前 task_type 的 init_status 查询飞书表格
- **AND** 将查询到的每条记录构造为 Task 对象
- **AND** 逐条调用 handler 处理，通过 TaskManager 管理 start/finish/fail
- **AND** 处理完成后才进入 ZMQ 主循环

#### Scenario: 无历史任务
- **WHEN** 启动时飞书表格中没有 init_status 对应的记录
- **THEN** 系统 SHALL 直接进入 ZMQ 主循环

#### Scenario: dingtalk_push task_type 配置映射
- **WHEN** `_get_worker_config()` 收到 task_type="dingtalk_push"
- **THEN** 系统 SHALL 返回 `config.dingtalk_worker` 配置对象

### Requirement: WorkerHandler 协议
系统 SHALL 定义 WorkerHandler 类型协议，签名为 `(Task, AppConfig) -> dict`，每个具体 worker 提供一个符合此签名的 handler 函数。

#### Scenario: handler 返回 outputs dict
- **WHEN** handler 成功执行完毕
- **THEN** handler SHALL 返回 dict 类型的 outputs，包含当前阶段的产出物

#### Scenario: handler 抛出异常表示失败
- **WHEN** handler 执行过程中遇到错误
- **THEN** handler SHALL 抛出异常，异常消息作为任务失败原因

### Requirement: WorkerConfig 基类
系统 SHALL 提供 WorkerConfig 基类，包含 pull_endpoint 和 push_endpoint 字段，各具体 worker 配置继承此基类。

#### Scenario: WorkerConfig 包含必要字段
- **WHEN** 定义具体 worker 的配置类
- **THEN** 该配置类 SHALL 继承 WorkerConfig，自动包含 pull_endpoint 和 push_endpoint
- **AND** 可添加该 worker 特有的配置字段
