## MODIFIED Requirements

### Requirement: 从 TikHub 获取创作者视频
系统 SHALL 调用 TikHub API 获取创作者最新视频列表，优先使用 APP v3 端点 `/api/v1/douyin/app/v3/fetch_user_post_videos`（参数：`sec_user_id`、`max_cursor`、`count`、`sort_type`），失败 3 次后降级到 Web 端点 `/api/v1/douyin/web/fetch_user_post_videos`（参数：`sec_user_id`、`max_cursor`、`count`、`filter_type`）。

#### Scenario: 从 TikHub 成功获取视频列表
- **WHEN** 系统使用有效的 `sec_user_id` 查询 TikHub API
- **THEN** 系统 SHALL 成功获取该创作者的最新视频列表
- **AND** 每条视频记录 SHALL 包含 `video_id`、`title`、`url`、`play_urls` 字段
- **AND** 视频列表按时间倒序排列（最新在前）

#### Scenario: TikHub API 返回错误
- **WHEN** TikHub API 调用失败（网络错误、频率限制、无效响应或主备接口均失败）
- **THEN** monitor SHALL 将该创作者标记为处理失败，记录错误信息，并继续处理下一创作者

#### Scenario: 视频列表为空
- **WHEN** TikHub API 返回成功但视频列表为空（创作者近期未发布新视频）
- **THEN** monitor SHALL 将该创作者视为已处理完成，无新视频
- **AND** 不向 ZMQ 推送任何任务
