## Why

当前 `TaskManager.start()` 只更新飞书的开始时间字段，不更新"状态"字段。`fail()` 统一写入"失败"，无法区分哪个阶段失败。用户在飞书表格中无法判断哪些任务正在执行、哪个阶段出了问题。

## What Changes

- 修改 `task_manager.py`：StageConfig 新增 `running_status` 和 `fail_status` 字段
- 修改 `TaskManager.start()`：将 `running_status` 写入飞书"状态"字段
- 修改 `TaskManager.fail()`：将阶段对应的 `fail_status` 写入飞书"状态"字段（替代硬编码"失败"）
- 统一状态命名规范：除"新视频"外，所有状态遵循 **交付物+动词+状态** 格式
- 修正 analyze 阶段 `finish_status` 从"分析完成"改为"报告分析完成"
- 飞书表格新增单选值："视频下载中"、"音频提取中"、"文字转写中"、"报告分析中"、"视频下载失败"、"音频提取失败"、"文字转写失败"、"报告分析失败"

## Capabilities

### New Capabilities

（无）

### Modified Capabilities
- `task-model`: StageConfig 新增 running_status/fail_status，start() 和 fail() 写入阶段专属状态

## Impact

- 修改文件：`task_manager.py`
- 飞书表格：新增 8 个单选值
- 无新文件、无新依赖
