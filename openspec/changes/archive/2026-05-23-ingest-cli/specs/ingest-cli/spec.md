## Purpose

提供 `python -m hot_pulse ingest` CLI 入口，支持用户手动提交视频分享链接，经 yt-dlp 解析后送入现有下载管道。

## ADDED Requirements

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

### Requirement: yt-dlp 链接解析

系统 SHALL 使用 `yt-dlp --dump-json` 解析 B站分享链接。

#### Scenario: 成功解析
- **WHEN** yt-dlp 正常返回 JSON
- **THEN** 系统 SHALL 从中提取直链 URL、title（API 输出）、video_id
- **AND** 直链 URL SHALL 放入 `Task.inputs.play_urls` 列表

#### Scenario: 解析失败
- **WHEN** yt-dlp 返回非零退出码或无有效 JSON
- **THEN** 系统 SHALL 打印错误信息并非零退出

### Requirement: Task 构造与 ZMQ 推送

系统 SHALL 构造 `Task(source="manual")` 并通过 ZMQ PUSH 推送到 `config.zeromq.push_endpoint`。

#### Scenario: 构造 Task
- **WHEN** 所有参数就绪
- **THEN** 构造的 Task SHALL 包含 `task_type="download"`、`source="manual"`、`platform=args.platform`
- **AND** `inputs.play_urls` SHALL 包含解析得到的直链 URL
- **AND** `creator` SHALL 为空字符串

#### Scenario: ZMQ 推送成功
- **WHEN** Task 构造完成并 ZMQ 推送成功
- **THEN** 系统 SHALL 在 stdout 输出 `{"task_id": "<uuid>", "status": "submitted"}`
- **AND** 以退出码 0 退出

#### Scenario: ZMQ 推送失败
- **WHEN** ZMQ 连接或推送失败
- **THEN** 系统 SHALL 打印错误日志并非零退出
