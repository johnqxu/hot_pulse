## Purpose

视频下载 worker，从 ZMQ 接收 download 类型 Task，执行视频下载，更新飞书记录，向下游发送 extract_audio 类型 Task。

## Requirements

### Requirement: Download Worker 主循环
系统 SHALL 提供 download worker，通过 `run_worker("download", handle_download)` 启动，handler 负责视频下载逻辑。

#### Scenario: 成功处理单个下载任务
- **WHEN** run_worker 调用 handle_download handler
- **THEN** handler SHALL 从 task.inputs["play_urls"] 获取下载地址列表
- **AND** 返回 outputs={"video_file": 本地文件路径}
- **AND** run_worker 负责 start/finish/build_next/send 逻辑

#### Scenario: Worker 优雅关闭
- **WHEN** worker 进程收到中断信号（SIGINT/SIGTERM）
- **THEN** run_worker SHALL 完成当前任务的处理后关闭 ZMQ 连接

### Requirement: 视频下载处理
系统 SHALL 提供 download worker 的 handler，从 Task.inputs 中获取 play_urls，按域名优先级排序后依次尝试下载视频。

#### Scenario: 按优先级排序下载
- **WHEN** play_urls 包含多个不同域名的 URL
- **THEN** 系统 SHALL 根据 config 中 url_priority 配置对 URL 按优先级降序排序
- **AND** 按排序后的顺序依次尝试下载

#### Scenario: URL 无匹配优先级配置
- **WHEN** 某 URL 的域名不匹配 url_priority 中的任何模式
- **THEN** 系统 SHALL 将该 URL 的优先级视为 0

#### Scenario: 优先级相同的 URL
- **WHEN** 多个 URL 的域名匹配到相同的优先级数值
- **THEN** 系统 SHALL 保持这些 URL 的原始顺序

#### Scenario: 所有地址均失败
- **WHEN** 排序后的所有 URL 均下载失败
- **THEN** 系统 SHALL 抛出 RuntimeError

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
系统 SHALL 支持通过 `python -m hot_pulse.download_worker` 独立启动 download worker。

#### Scenario: 以 CLI 方式运行
- **WHEN** 用户执行 `python -m hot_pulse.download_worker`
- **THEN** 系统 SHALL 调用 `run_worker("download", handle_download)`
