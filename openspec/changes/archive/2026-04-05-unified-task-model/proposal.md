## Why

当前 monitor 中的 ZMQ 消息是手写的临时字典，飞书记录是独立的数据模型（VideoRecord），两者之间没有统一抽象。后续阶段（下载、音频提取、转写、分析）都需要"接收任务 → 处理 → 更新飞书 → 推送下一阶段"的相同模式。需要一个统一的任务模型作为流水线的核心抽象，避免每个阶段重复实现飞书同步、状态管理、日志等公共逻辑。

## What Changes

- 新增 `task.py`：定义 Task Pydantic Model，作为流水线中统一的消息信封
- 新增 `task_manager.py`：定义 TaskManager，封装任务生命周期管理（开始/完成/失败时的飞书同步和日志）
- 新增 `stage_config.py`：定义阶段配置映射（每个 task_type 对应的飞书字段、输入输出定义）
- 修改 `feishu.py`：新增按 record_id 更新记录的方法，create_records 返回 record_id
- 修改 `monitor.py`：ZMQ 消息从手写 dict 改为 Task 序列化，写入飞书后捕获 record_id 填入 Task
- 修改 `zmq_client.py`：支持发送/接收 Task 对象（自动序列化/反序列化）

## Capabilities

### New Capabilities
- `task-model`: 统一任务模型和生命周期管理，包括 Task 数据模型、TaskManager 能力层、阶段配置映射

### Modified Capabilities
- `douyin-monitor`: monitor 产出的 ZMQ 消息改为统一 Task 格式
- `zeromq-publisher`: 支持发送/接收 Task 对象序列化

## Impact

- Task 是纯内存模型，不做持久化；飞书表格是唯一持久化真相来源
- 后续阶段（download 等）可直接基于 Task + TaskManager 构建，无需关心飞书字段映射细节
- 对现有 monitor 的行为无功能性变更（仅消息格式标准化）
