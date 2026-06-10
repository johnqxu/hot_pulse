## Context

patrol_worker 是 pipeline-executor 架构迁移后最后一个仍使用 ZMQ 的模块。当前 patrol_worker 的架构分两层：

1. **检测层**：从飞书查询 running/fail 状态的记录，根据时间戳判断僵尸任务
2. **执行层**：通过 ZMQ PUSH socket 将恢复的 Task 发送到独立 worker 进程

pipeline-executor 改动后，monitor.py 已改为直接调用 `pipeline.run_subscription_pipeline(task, config)`，worker 不再是独立常驻进程，handler 函数由 pipeline 直接调用。patrol_worker 的执行层仍依赖已废弃的 ZMQ 多进程架构。

## Goals / Non-Goals

**Goals:**
- 移除 patrol_worker 对 ZMQ 的依赖，删除 `_build_push_routes()`、`_close_push_routes()`、`STAGE_REVERSE` 及所有 `zmq` 相关代码
- 巡检恢复改为直接调用 `pipeline.run_subscription_pipeline(task, config, start_stage)` 或 `pipeline.run_manual_pipeline(task, config, start_stage)`
- 复用 `pipeline.STATUS_TO_STAGE` 映射替代自建的 `STAGE_REVERSE`（需扩展：加入 fail_status）
- 复用 `feishu._record_to_task()` 替代自建的 `_build_task_from_record()`

**Non-Goals:**
- 不修改巡检间隔（保持 60 分钟）
- 不引入异步/线程池（串行阻塞恢复，方案 A）
- 不修改 pipeline.py 的核心执行逻辑
- 不改动 monitor.py、ingest.py、main.py
- 不移除 pyzmq 依赖（不在 pyproject.toml 中，无需处理）

## Decisions

### 决策 1: 直接函数调用替代 ZMQ PUSH

**选择**：patrol_worker 发现僵尸任务后直接调用 `pipeline.run_subscription_pipeline(task, config, start_stage)`。

**备选方案**：
- **ZMQ PUSH（当前方案）**：与单进程管道架构不一致，需额外维护 ZMQ socket 和路由映射
- **独立线程池**：增加复杂度，巡检场景下僵尸任务数量极少（通常 0~2 个），收益不大
- **asyncio 协程**：Python 同步生态下引入异步收益有限，且 worker handler 均为同步阻塞函数

**理由**：pipeline.py 已提供 `start_stage` 参数支持从中间阶段恢复，patrol_worker 直接复用即可。串行阻塞恢复简单可靠，符合巡检低频场景。

### 决策 2: 扩展 pipeline.STATUS_TO_STAGE 覆盖 fail_status

**选择**：将 `pipeline._STATUS_TO_STAGE` 改为公开常量 `STATUS_TO_STAGE`，并**扩展**加入所有 fail_status 映射。patrol_worker 直接引用，替代自建的 `STAGE_REVERSE`。

**理由**：
- `STAGE_REVERSE` 和 `STATUS_TO_STAGE` 功能重叠（飞书状态→阶段名映射），但 `STATUS_TO_STAGE` 缺少 fail_status
- `STAGE_MAPPING` 已定义所有 fail_status，补充映射即可
- 集中维护避免 patrol 和 pipeline 各自维护一份不一致的映射

**变更**：
1. `pipeline.py` 中将 `_STATUS_TO_STAGE` 重命名为 `STATUS_TO_STAGE`
2. 补充 fail_status 条目：`"视频下载失败": "download"`, `"音频提取失败": "extract_audio"`, `"文字转写失败": "transcribe"`, `"报告分析失败": "analyze"`, `"报告推送失败": "dingtalk_push"`, `"知识整理失败": "knowledge"`
3. 更新 `_NON_TERMINAL_STATUSES` 只保留非终端状态（排除 fail_status）

### 决策 3: patrol_worker 保留简化版飞书查询，复用 `_record_to_task()`

**选择**：patrol_worker 不直接使用 `feishu.query_records_by_status()`（它返回 Task 对象，不包含时间戳字段），而是保留一个简化版查询返回 raw fields dict，供 `_is_zombie()` 做僵尸检测。构造 Task 时复用 `feishu._record_to_task()`。

**备选方案**：
- **全量使用 `feishu.query_records_by_status()`**：返回的 Task 不含时间戳，`_is_zombie()` 无法工作（审核发现 CRITICAL 问题）
- **给 Task 模型加 `extra_fields`**：侵入性太大，Task 不应承载飞书 raw fields
- **`_is_zombie()` 改为额外查询飞书时间戳字段**：每轮巡检对每条记录做额外 API 调用，不必要

**理由**：
- `_is_zombie()` 本质需要飞书 raw fields 中的毫秒时间戳，这是飞书特有的数据格式，不应泄漏到 Task 模型
- patrol 当前的 `_query_records_by_status()` 逻辑简单且正确，保留但简化
- `_build_task_from_record()` 和 `feishu._record_to_task()` 是功能重复的代码，统一使用 feishu 的版本

**变更**：
1. patrol_worker 保留简化版 `_query_records_by_status(status)` → `list[tuple[str, dict]]`（返回 `(record_id, fields)` 列表）
2. 删除 `_build_task_from_record()`，改用 `from hot_pulse.feishu import _record_to_task`
3. feishu.py 的 `_record_to_task()` 需补充 `source` 字段解析（当前已实现，无需改动）

### 决策 4: Task.source 字段回退处理

**选择**：patrol_worker 通过 `feishu._record_to_task()` 构造 Task，该函数已处理 `source` 字段默认值（`_extract_text(fields.get("来源", "")) or "subscription"`）。

## Risks / Trade-offs

**[风险] 长时间阻塞巡检周期**
→ 如果恢复的 download 任务耗时 20 分钟，下轮巡检会延迟。但僵尸任务通常极少（worker 崩溃才产生），实际影响有限。可接受。

**[风险] knowledge 阶段恢复**
→ 扩展后的 `STATUS_TO_STAGE` 和 `pipeline.run_*_pipeline()` 均已覆盖 knowledge 阶段（manual 管道），不影响恢复。

**[风险] ZMQ socket 移除后旧 worker 进程残留**
→ 旧部署中可能有 download_worker、transcribe_worker 等独立进程在运行。迁移后这些进程不再被 patrol_worker 推送任务，应手动停止。新部署中 patrol_worker 是独立进程，通过 `hot-pulse-patrol` CLI 入口启动。

**[权衡] `_record_to_task()` 作为非公开 API**
→ `feishu._record_to_task()` 以下划线开头，语义上是模块内部函数。本设计中 patrol 显式引用它，表明它是跨模块共用的内部 API。如需更明确，可在 feishu.py 的 `__all__` 或文档中标注。
