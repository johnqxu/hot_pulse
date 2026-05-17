## Purpose

TikHub API 调用层提供主备接口自动降级能力：优先使用 APP v3 接口，重试 3 次失败后自动切换到 Web 备用接口。

## ADDED Requirements

### Requirement: 主接口调用

系统 SHALL 使用修正后的参数名调用 TikHub APP v3 接口 `/api/v1/douyin/app/v3/fetch_user_post_videos`，参数为 `sec_user_id`（必填）、`max_cursor`（默认 0）、`count`（默认配置值）、`sort_type`（默认 0=最新排序）。

#### Scenario: 主接口成功返回
- **WHEN** APP v3 接口返回 200 状态码
- **THEN** 系统 SHALL 从响应 `data.aweme_list`（回退 `data.videos`、`data.list`）中解析视频列表
- **AND** 按 `max_count` 截断超出的视频数量

#### Scenario: 主接口返回非 200
- **WHEN** APP v3 接口返回非 200 状态码
- **THEN** 系统 SHALL 记录 error 日志（含状态码和响应体前 1000 字符）
- **AND** 触发重试机制

### Requirement: 主接口重试机制

系统 SHALL 对主接口调用进行最多 3 次重试，使用指数退避策略（2^N 秒）。

#### Scenario: 主接口重试后成功
- **WHEN** 第 1 次或第 2 次主接口调用失败
- **THEN** 系统 SHALL 等待 2^attempt 秒后重试
- **AND** 重试成功后返回视频列表

#### Scenario: 主接口 3 次全部失败
- **WHEN** 主接口连续 3 次调用均失败
- **THEN** 系统 SHALL 记录 error 日志后进入备用接口降级

### Requirement: 备用接口降级

系统 SHALL 在主接口 3 次重试全部失败后，自动调用 Web 备用接口 `/api/v1/douyin/web/fetch_user_post_videos`，参数为 `sec_user_id`（必填）、`max_cursor`（默认 0）、`count`（默认配置值）、`filter_type`（默认 0=默认排序）。

#### Scenario: 备用接口成功返回
- **WHEN** Web 接口返回 200 状态码
- **THEN** 系统 SHALL 解析视频列表并返回结果
- **AND** 记录 info 日志表明使用备用接口成功

#### Scenario: 备用接口失败
- **WHEN** Web 接口返回非 200 状态码或网络异常
- **THEN** 系统 SHALL 抛出异常（主备均失败）
- **AND** 异常信息 SHALL 同时包含主接口和备用接口的错误原因

#### Scenario: 备用接口被禁用
- **WHEN** `config.tikhub.fallback_endpoint` 配置为空字符串
- **THEN** 系统 SHALL 跳过备用接口降级，直接抛出主接口的异常
