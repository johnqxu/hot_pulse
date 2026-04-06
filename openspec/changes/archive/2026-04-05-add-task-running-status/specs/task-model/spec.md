## MODIFIED Requirements

### Requirement: 阶段配置映射
系统 SHALL 提供 STAGE_MAPPING 配置，声明每个 task_type 对应的飞书字段映射、状态映射和下一阶段路由。所有状态值（"新视频"除外）遵循 **交付物+动词+状态** 命名规范。

#### Scenario: download 阶段配置
- **WHEN** task_type 为 "download"
- **THEN** STAGE_MAPPING SHALL 包含 init_status="新视频"、running_status="视频下载中"、finish_status="视频下载完成"、fail_status="视频下载失败"、start_field="视频下载开始时间"、end_field="视频下载完成时间"、output_map={"video_file": "视频文件地址"}、next_type="extract_audio"

#### Scenario: extract_audio 阶段配置
- **WHEN** task_type 为 "extract_audio"
- **THEN** STAGE_MAPPING SHALL 包含 init_status="视频下载完成"、running_status="音频提取中"、finish_status="音频提取完成"、fail_status="音频提取失败"、start_field="音频提取开始时间"、end_field="音频提取完成时间"、output_map={"audio_file": "音频文件地址"}、next_type="transcribe"

#### Scenario: transcribe 阶段配置
- **WHEN** task_type 为 "transcribe"
- **THEN** STAGE_MAPPING SHALL 包含 init_status="音频提取完成"、running_status="文字转写中"、finish_status="文字转写完成"、fail_status="文字转写失败"、start_field="文字转写开始时间"、end_field="文字转写完成时间"、output_map={"text_file": "文字文件地址"}、next_type="analyze"

#### Scenario: analyze 阶段配置
- **WHEN** task_type 为 "analyze"
- **THEN** STAGE_MAPPING SHALL 包含 init_status="文字转写完成"、running_status="报告分析中"、finish_status="报告分析完成"、fail_status="报告分析失败"、start_field="内容分析开始时间"、end_field="内容分析结束时间"、output_map={"report_file": "分析报告地址"}、next_type=None

### Requirement: TaskManager 任务生命周期管理
系统 SHALL 提供 TaskManager 封装任务在 start/finish/fail 状态流转时的飞书同步和日志输出。

#### Scenario: 任务开始
- **WHEN** 调用 TaskManager.start(task)
- **THEN** 系统 SHALL 更新 task.status="running"，PATCH 飞书记录的开始时间字段和"状态"字段（设为 running_status），输出日志

#### Scenario: 任务完成
- **WHEN** 调用 TaskManager.finish(task, outputs)
- **THEN** 系统 SHALL 更新 task.status="done"，将 outputs 按阶段 output_map 写入飞书记录，更新结束时间字段，将 finish_status 写入飞书"状态"字段，输出日志

#### Scenario: 任务失败
- **WHEN** 调用 TaskManager.fail(task, error)
- **THEN** 系统 SHALL 更新 task.status="failed"，将 fail_status 写入飞书"状态"字段，输出日志
