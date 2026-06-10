## 1. Pipeline 模块适配

- [x] 1.1 将 `pipeline._STATUS_TO_STAGE` 重命名为 `pipeline.STATUS_TO_STAGE`，并加入 fail_status 映射：`"视频下载失败"`、`"音频提取失败"`、`"文字转写失败"`、`"报告分析失败"`、`"报告推送失败"`、`"知识整理失败"`
- [x] 1.2 更新 `pipeline._NON_TERMINAL_STATUSES` 基于扩展后的 `STATUS_TO_STAGE` 构建（只包含 init/running 状态，排除 fail）
- [x] 1.3 更新 `pipeline.recover_interrupted_tasks()` 中对 `_STATUS_TO_STAGE` 的内部引用

## 2. Patrol Worker 核心改造

- [x] 2.1 删除 `import zmq`、`import uuid` 等不再需要的 import
- [x] 2.2 删除 `STAGE_REVERSE` 及 `_build_reverse_map()` 函数
- [x] 2.3 删除 `_build_push_routes()` 和 `_close_push_routes()` 函数
- [x] 2.4 删除 `_build_task_from_record()` 函数，改用 `from hot_pulse.feishu import _record_to_task`
- [x] 2.5 简化 `_query_records_by_status()`：删除 page_size 400 硬限制，返回类型改为 `list[tuple[str, dict]]`（`(record_id, fields)`），删除 `_extract_text` 重复调用
- [x] 2.6 重写 `run_patrol()` 函数：
  - 使用 `pipeline.STATUS_TO_STAGE` 获取需要扫描的状态列表
  - 对每种状态调用 `_query_records_by_status()` 获取 `(record_id, fields)` 列表
  - running 状态的僵尸检测通过 `_is_zombie(fields, start_field, threshold)`（保持对 fields dict 的访问）
  - 通过 `STAGE_MAPPING` 获取 start_field 和 init_status（`_is_zombie()` 和回退均需要）
  - 僵尸/失败任务：回退飞书状态后，用 `_record_to_task(fields, record_id, task_type)` 构造 Task，直接调用 `pipeline.run_subscription_pipeline()` 或 `pipeline.run_manual_pipeline()`
- [x] 2.7 `_is_zombie()` 保持不变（继续接收 fields dict 参数）

## 3. 清理与验证

- [x] 3.1 完整通读 `patrol_worker.py`，确保无残留 ZMQ 引用
- [x] 3.2 运行 `uv run python -c "from hot_pulse.patrol_worker import run_patrol; print('import OK')"` 验证导入无错误
- [x] 3.3 运行 `uv run python -c "from hot_pulse.pipeline import STATUS_TO_STAGE; assert '视频下载失败' in STATUS_TO_STAGE; print('STATUS_TO_STAGE OK')"` 验证 fail 映射
