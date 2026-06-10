## Purpose

提供 `python -m hot_pulse ingest` CLI 入口，支持用户手动提交视频分享链接，经 yt-dlp 解析元信息后送入标准下载管道。

## Requirements

### Requirement: CLI 参数解析

系统 SHALL 支持 `python -m hot_pulse ingest` 命令，接收以下参数。

#### Scenario: 必填参数
- **WHEN** 用户执行 `python -m hot_pulse ingest`
- **THEN** 系统 SHALL 要求提供 `--type`（值 `video`）、`--platform`（值 `bilibili`）、`--url`
- **AND** 缺少任一必填参数时 SHALL 非零退出并打印用法

#### Scenario: 可选参数
- **WHEN** 用户传 `--title "xxx"`
- **THEN** 系统 SHALL 使用该值作为 Task.title
- **WHEN** 用户未传 `--title`
- **THEN** 系统 SHALL 用 yt-dlp 解析结果中的标题填充 Task.title

#### Scenario: notes 参数
- **WHEN** 用户传 `--notes "xxx"`
- **THEN** 系统 SHALL 将值写入 `Task.inputs["notes"]`
- **WHEN** 用户未传 `--notes`
- **THEN** Task.inputs.notes SHALL 为空字符串

### Requirement: yt-dlp 元信息解析

系统 SHALL 使用 `yt-dlp --dump-json` 解析 B站分享链接，仅提取元信息（不下载）。

#### Scenario: 成功解析
- **WHEN** yt-dlp 正常返回 JSON
- **THEN** 系统 SHALL 从中提取 video_id、title、uploader
- **AND** 原始分享链接 SHALL 放入 `Task.inputs.play_urls` 列表

#### Scenario: 解析失败
- **WHEN** yt-dlp 返回非零退出码或无有效 JSON
- **THEN** 系统 SHALL 打印错误信息并非零退出

### Requirement: 飞书记录创建

系统 SHALL 在提交 Task 前创建飞书记录，记录来源信息。

#### Scenario: 飞书记录字段
- **WHEN** ingest 提交视频
- **THEN** 飞书记录 SHALL 包含 `博主=uploader`、`来源=manual`、`视频链接=原分享链接`、`平台=platform`

### Requirement: Task 构造与管道执行

系统 SHALL 构造 `Task(source="manual")` 并同步调用 `run_manual_pipeline(task, config)` 执行完整处理管道。

#### Scenario: 构造 Task
- **WHEN** 所有参数就绪
- **THEN** 构造的 Task SHALL 包含 `task_type="download"`、`source="manual"`、`platform=args.platform`
- **AND** `creator` SHALL 为 yt-dlp 解析出的 uploader

#### Scenario: 下载分流
- **WHEN** Task 到达 download handler 且 `source="manual"`
- **THEN** download handler SHALL 使用 yt-dlp 下载（合并音视频），而非 httpx 直链

#### Scenario: 管道执行成功
- **WHEN** Task 构造完成并 `run_manual_pipeline(task, config)` 执行成功
- **THEN** 系统 SHALL 以退出码 0 退出
- **AND** 日志中输出 pipeline 各阶段执行结果

#### Scenario: 管道执行失败
- **WHEN** pipeline 某个阶段执行失败
- **THEN** 系统 SHALL 以非零退出码退出
- **AND** 失败信息由 TaskManager 记录到飞书记录
