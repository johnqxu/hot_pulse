## Purpose

视频下载 handler，由 `pipeline._run_stages()` 在 download 阶段调用，执行视频下载，返回 outputs 供 TaskManager 更新飞书记录并构建下一阶段 Task。

## Requirements

### Requirement: Download Handler

系统 SHALL 提供 `handle_download(task, config)` handler 函数，由 `pipeline._run_stages()` 调用，负责视频下载逻辑。

#### Scenario: 成功处理单个下载任务
- **WHEN** pipeline 调用 handle_download handler
- **THEN** handler SHALL 从 task.inputs["play_urls"] 获取下载地址列表
- **AND** 返回 outputs={"video_file": 本地文件路径}
- **AND** pipeline 负责 start/finish/build_next 逻辑

#### Scenario: Handler 执行失败
- **WHEN** handler 执行过程中抛出异常
- **THEN** pipeline SHALL 调用 TaskManager.fail() 标记失败并停止后续阶段

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

### Requirement: Download Handler 可独立调用

`handle_download(task, config)` SHALL 作为纯函数，支持被 pipeline 调用或测试中独立调用。

#### Scenario: 被 pipeline 调用
- **WHEN** pipeline 执行 download 阶段
- **THEN** 系统 SHALL 直接调用 `handle_download(task, config)`
