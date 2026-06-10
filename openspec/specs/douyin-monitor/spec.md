## Purpose

监控抖音创作者的新视频发布情况，通过 TikHub API 获取最新视频列表，与飞书多维表格中的已有记录进行对比，写入新发现的视频记录。

## Requirements

### Requirement: 从 TikHub 获取创作者视频
系统 SHALL 调用 TikHub API 获取创作者最新视频列表，优先使用 APP v3 端点 `/api/v1/douyin/app/v3/fetch_user_post_videos`（参数：`sec_user_id`、`max_cursor`、`count`、`sort_type`），失败 3 次后降级到 Web 端点 `/api/v1/douyin/web/fetch_user_post_videos`（参数：`sec_user_id`、`max_cursor`、`count`、`filter_type`）。

#### Scenario: 从 TikHub 成功获取视频列表
- **WHEN** 系统使用有效的 `sec_user_id` 查询 TikHub API
- **THEN** 系统 SHALL 成功获取该创作者的最新视频列表
- **AND** 每条视频记录 SHALL 包含 `video_id`、`title`、`url`、`play_urls` 字段
- **AND** 视频列表按时间倒序排列（最新在前）

#### Scenario: play_addr_h264 节点缺失
- **WHEN** 视频条目不包含 `video.play_addr_h264` 节点
- **THEN** 系统 SHALL 降级使用 `video.play_addr.url_list`
- **AND** 若该节点也缺失，系统 SHALL 存储空 JSON 数组 `[]`

#### Scenario: TikHub API 返回错误
- **WHEN** TikHub API 调用失败（网络错误、频率限制、无效响应或主备接口均失败）
- **THEN** monitor SHALL 将该创作者标记为处理失败，记录错误信息，并继续处理下一创作者

#### Scenario: 视频列表为空
- **WHEN** TikHub API 返回成功但视频列表为空（创作者近期未发布新视频）
- **THEN** monitor SHALL 将该创作者视为已处理完成，无新视频
- **AND** 不触发 pipeline

### Requirement: 通过对比已有记录检测新视频
系统 SHALL 查询飞书多维表格中每个博主已有的视频 ID，计算差集以识别新发布的视频。

#### Scenario: 未发现新视频
- **WHEN** TikHub 返回的所有视频在飞书多维表格中已存在
- **THEN** 系统 SHALL 跳过写入并记录日志"博主 {creator_name} 无新视频"

#### Scenario: 发现新视频
- **WHEN** TikHub 返回的视频 ID 在飞书多维表格中不存在
- **THEN** 系统 SHALL 将这些视频标记为新视频并准备写入

#### Scenario: 首次运行无已有记录
- **WHEN** 飞书多维表格中该博主没有任何记录
- **THEN** TikHub 返回的所有视频 SHALL 被视为新视频

### Requirement: 将新视频记录写入飞书多维表格
系统 SHALL 将每条新视频作为一条新记录写入飞书多维表格，按照字段映射填充字段。

#### Scenario: 写入单条新视频记录
- **WHEN** 检测到某个创作者有新视频
- **THEN** 系统 SHALL 按照字段映射创建包含所有字段的记录
- **AND** 飞书写入成功后，系统 SHALL 捕获飞书返回的 record_id
- **AND** 系统 SHALL 构造 Task 对象（task_type="download"，feishu_record_id=record_id，inputs 包含 play_urls）
- **AND** 调用 `run_subscription_pipeline(task, config)` 串行执行完整处理管道

#### Scenario: 写入多条新视频
- **WHEN** 检测到某个创作者有多条新视频
- **THEN** 系统 SHALL 将每条视频分别写入飞书多维表格
- **AND** 对每条新视频依次调用 `run_subscription_pipeline(task, config)`

#### Scenario: 飞书 API 写入失败
- **WHEN** 写入飞书多维表格失败
- **THEN** 系统 SHALL 记录错误日志，且不触发该视频的 pipeline
- **AND** 继续处理剩余新视频
- **AND** 系统 SHALL NOT 在下次运行时跳过已写入的记录（幂等性）

#### Scenario: Pipeline 执行失败
- **WHEN** pipeline 某个阶段执行失败
- **THEN** 系统 SHALL 记录错误日志但不阻塞监控工作流
- **AND** 继续处理剩余新视频

### Requirement: 支持独立 CLI 和可导入模块两种运行方式
监控模块 SHALL 支持通过 `python -m hot_pulse.monitor` 独立执行，以及通过 `from hot_pulse.monitor import run_monitor` 编程调用。

#### Scenario: 以 CLI 方式运行
- **WHEN** 用户执行 `python -m hot_pulse.monitor`
- **THEN** 系统 SHALL 加载配置，遍历所有创作者，检测新视频，写入飞书

#### Scenario: 以导入模块方式运行
- **WHEN** 其他模块调用 `run_monitor()`
- **THEN** 系统 SHALL 执行相同的监控工作流并返回结果摘要

### Requirement: 遍历所有配置的创作者
系统 SHALL 按顺序处理每个配置的创作者，确保单个创作者的失败不会阻止后续创作者的处理。

#### Scenario: 某个创作者失败，其余成功
- **WHEN** 处理创作者 A 失败（API 错误、无效 sec_uid 等）
- **THEN** 系统 SHALL 记录创作者 A 的错误日志，继续处理创作者 B、C 等
- **AND** 系统 SHALL 在结束时报告摘要，说明哪些创作者成功、哪些失败

### Requirement: Pipeline 配置
系统 SHALL 从 config.yaml 加载配置，monitor 直接调用 `run_subscription_pipeline()` 执行处理管道，无需 ZMQ 中间层。

#### Scenario: Pipeline 正常执行
- **WHEN** monitor 完成飞书写入后调用 `run_subscription_pipeline(task, config)`
- **THEN** 系统 SHALL 按 download → extract_audio → transcribe → analyze → dingtalk_push 顺序执行各阶段

#### Scenario: Pipeline 不可用时降级
- **WHEN** pipeline 模块导入失败
- **THEN** 系统 SHALL 记录错误日志，仅完成飞书写入（不触发后续处理）
