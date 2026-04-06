## ADDED Requirements

### Requirement: Download Worker 主循环
系统 SHALL 提供常驻 download worker 进程，持续从 ZMQ PULL socket 接收 download 类型 Task，执行视频下载，并推送下一阶段 Task。

#### Scenario: 成功处理单个下载任务
- **WHEN** worker 从 ZMQ PULL 收到 task_type="download" 的 Task
- **THEN** 系统 SHALL 调用 TaskManager.start() 标记开始
- **AND** 从 task.inputs["play_urls"] 获取下载地址列表
- **AND** 按顺序逐个尝试下载，首个成功即停止
- **AND** 调用 TaskManager.finish() 写入 outputs={"video_file": 本地文件路径}
- **AND** 调用 TaskManager.build_next() 构造下一阶段 Task
- **AND** 通过 ZMQ PUSH 发送下一阶段 Task

#### Scenario: 所有下载地址均失败
- **WHEN** play_urls 中所有 URL 下载均失败
- **THEN** 系统 SHALL 调用 TaskManager.fail() 标记失败
- **AND** 继续处理下一个 Task

#### Scenario: 收到非 download 类型的 Task
- **WHEN** worker 收到 task_type 不是 "download" 的 Task
- **THEN** 系统 SHALL 记录警告日志并跳过该 Task

#### Scenario: Worker 优雅关闭
- **WHEN** worker 进程收到中断信号（SIGINT/SIGTERM）
- **THEN** 系统 SHALL 完成当前任务的处理后关闭 ZMQ 连接

### Requirement: HTTP 流式视频下载
系统 SHALL 使用 httpx 流式下载视频文件，避免将整个文件加载到内存。

#### Scenario: 单个 URL 下载成功
- **WHEN** 使用 httpx stream GET 请求下载视频
- **THEN** 系统 SHALL 以流式方式将响应体写入本地文件
- **AND** 文件路径为 `{download_dir}/{video_id}.mp4`

#### Scenario: 单个 URL 下载失败，尝试下一个
- **WHEN** 当前 URL 下载失败（网络错误、HTTP 错误、超时）
- **THEN** 系统 SHALL 记录警告日志，尝试 play_urls 列表中的下一个 URL

#### Scenario: 下载目录不存在
- **WHEN** 配置的下载目录不存在
- **THEN** 系统 SHALL 自动创建目录

### Requirement: Download Worker 独立运行入口
系统 SHALL 支持通过 `python -m hot_pulse.download_worker` 独立启动 download worker，也支持通过 `run_download_worker()` 函数被编排调用。

#### Scenario: 以 CLI 方式运行
- **WHEN** 用户执行 `python -m hot_pulse.download_worker`
- **THEN** 系统 SHALL 加载配置，初始化 ZMQ 和飞书连接，进入主循环

#### Scenario: 以函数调用方式运行
- **WHEN** 其他模块调用 `run_download_worker(config_path)`
- **THEN** 系统 SHALL 执行相同的工作流
