## ADDED Requirements

### Requirement: 统一任务数据模型
系统 SHALL 提供 Task Pydantic Model 作为流水线各阶段间传递的统一消息信封，包含身份标识、源信息、阶段依赖/产出、状态等字段。

#### Scenario: 从 ZMQ 消息反序列化
- **WHEN** 从 ZMQ socket 接收到 JSON 字节流
- **THEN** 系统 SHALL 通过 `Task.model_validate_json()` 反序列化为 Task 对象

#### Scenario: 序列化为 ZMQ 消息
- **WHEN** 需要通过 ZMQ 发送 Task
- **THEN** 系统 SHALL 通过 `task.model_dump_json()` 序列化为 JSON 字节流

### Requirement: 阶段配置映射
系统 SHALL 提供 STAGE_MAPPING 配置，声明每个 task_type 对应的飞书字段映射和下一阶段路由。

#### Scenario: download 阶段配置
- **WHEN** task_type 为 "download"
- **THEN** STAGE_MAPPING SHALL 包含 start_field="视频下载开始时间"、end_field="视频下载完成时间"、output_map={"video_file": "视频文件地址"}、next_type="extract_audio"

#### Scenario: extract_audio 阶段配置
- **WHEN** task_type 为 "extract_audio"
- **THEN** STAGE_MAPPING SHALL 包含 start_field="音频提取开始时间"、end_field="音频提取完成时间"、output_map={"audio_file": "音频文件地址"}、next_type="transcribe"

#### Scenario: transcribe 阶段配置
- **WHEN** task_type 为 "transcribe"
- **THEN** STAGE_MAPPING SHALL 包含 start_field="文字转写开始时间"、end_field="文字转写完成时间"、output_map={"text_file": "文字文件地址"}、next_type="analyze"

#### Scenario: analyze 阶段配置
- **WHEN** task_type 为 "analyze"
- **THEN** STAGE_MAPPING SHALL 包含 start_field="内容分析开始时间"、end_field="内容分析结束时间"、output_map={"report_file": "分析报告地址"}、next_type=None

### Requirement: TaskManager 任务生命周期管理
系统 SHALL 提供 TaskManager 封装任务在 start/finish/fail 状态流转时的飞书同步和日志输出。

#### Scenario: 任务开始
- **WHEN** 调用 TaskManager.start(task)
- **THEN** 系统 SHALL 更新 task.status="running"，PATCH 飞书记录的开始时间字段和状态，输出日志

#### Scenario: 任务完成
- **WHEN** 调用 TaskManager.finish(task, outputs)
- **THEN** 系统 SHALL 更新 task.status="done"，将 outputs 按阶段 output_map 写入飞书记录，更新结束时间字段，输出日志

#### Scenario: 任务失败
- **WHEN** 调用 TaskManager.fail(task, error)
- **THEN** 系统 SHALL 更新 task.status="failed"，PATCH 飞书记录状态和错误信息，输出日志

#### Scenario: 构建下一阶段任务
- **WHEN** 调用 TaskManager.build_next(task) 且当前阶段有 next_type
- **THEN** 系统 SHALL 基于当前 task 的 outputs 和 STAGE_MAPPING 的 next_input_map 构造新的 Task 对象，task_type 为 next_type，inputs 从当前 outputs 映射

#### Scenario: 最后一个阶段无下一阶段
- **WHEN** 调用 TaskManager.build_next(task) 且当前阶段的 next_type 为 None
- **THEN** 系统 SHALL 返回 None
