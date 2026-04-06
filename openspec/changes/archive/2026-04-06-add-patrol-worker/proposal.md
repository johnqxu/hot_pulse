## Why

Worker 进程可能在任务执行中崩溃或被强制终止，导致飞书表格中出现停留在 running 状态的僵尸任务或 fail 状态的失败任务。当前只有在 worker 重启时才会恢复 init_status 的任务，running 和 fail 状态的任务永远不会被重新处理。需要一个巡检机制自动发现并恢复这些任务。

## What Changes

- 新增 `src/hot_pulse/patrol_worker.py` 巡检 worker：
  - 每小时扫描飞书表格所有记录
  - 检测停滞超过 90 分钟的 running 状态任务（僵尸任务）
  - 检测 fail 状态的任务
  - 将飞书状态回退到该阶段的 init_status
  - 构造 Task 对象，通过 ZMQ PUSH 推送到对应 worker 的 pull_endpoint
- 新增巡检相关的配置项（巡检间隔、僵尸阈值）
- 与 monitor 同模式：飞书改状态 + ZMQ 通知

## Capabilities

### New Capabilities
- `patrol-worker`: 僵尸/失败任务巡检与恢复

### Modified Capabilities
（无需修改现有 spec，各 worker 和 monitor 的行为不变）

## Impact

- 新增文件：`src/hot_pulse/patrol_worker.py`
- 修改文件：`src/hot_pulse/config.py`（新增 PatrolWorkerConfig）、`config.yaml`
- 修改文件：`src/hot_pulse/main.py`（启动 patrol worker 子进程）
- 技术债务：暂不实现重试次数上限，后续补充

## Tech Debt

- **重试次数上限**：当前不限制重试次数，反复失败的任务会无限循环。后续需要在飞书表格中增加"重试次数"字段，超过阈值后标记为终止态。
