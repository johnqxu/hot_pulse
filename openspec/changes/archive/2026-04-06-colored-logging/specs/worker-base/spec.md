## MODIFIED Requirements

### Requirement: Worker 日志标识

每个 worker 子进程 SHALL 使用带颜色的进程标识前缀输出日志。不同 task_type 对应不同颜色：download=青色、extract_audio=黄色、transcribe=蓝色、analyze=洋红、dingtalk_push=红色。

#### Scenario: Worker 启动日志
- **WHEN** worker 子进程启动
- **THEN** 日志格式为 `{time} | {level} | <color>[task_type]</color> {message}`，颜色按 task_type 映射

#### Scenario: 独立运行 worker
- **WHEN** 通过 `python -m hot_pulse.xxx_worker` 独立启动
- **THEN** 日志同样使用对应颜色的 `[task_type]` 前缀
