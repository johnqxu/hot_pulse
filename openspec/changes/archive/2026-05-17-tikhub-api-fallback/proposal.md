## Why

当前 TikHub APP v3 接口 `fetch_user_post_videos` 频繁返回 400 错误，且请求参数名与最新 API 文档不一致（`cursor`/`max_count` vs 文档要求的 `max_cursor`/`count`）。需要修正参数名并增加 Web 版 API 作为降级备用，提高视频获取的可靠性。

## What Changes

- 修正主接口请求参数：`cursor` → `max_cursor`，`max_count` → `count`，新增 `sort_type`（默认 0=最新排序）
- 新增备用接口 `/api/v1/douyin/web/fetch_user_post_videos`（Web 版），参数为 `max_cursor`、`count`、`filter_type`
- `fetch_user_post_videos` 中主接口重试 3 次全部失败后，自动切换调用备用接口（不重试，单次调用）
- 视频列表解析保持兼容：同时支持 `aweme_list`、`videos`、`list` 三种字段名
- `TikHubConfig` 新增 `fallback_endpoint` 和 `timeout` 配置字段

## Capabilities

### New Capabilities

- `tikhub-api-fallback`: TikHub API 调用失败时自动降级到备用 Web 接口，主备接口参数名按最新文档修正

### Modified Capabilities

- `douyin-monitor`: TikHub API 调用需求更新——参数名修正为主接口 `max_cursor`/`count`/`sort_type`，备用接口 `max_cursor`/`count`/`filter_type`

## Impact

- **代码**: `tikhub.py` — `_do_fetch` 拆分为 `_do_fetch_primary` + `_do_fetch_fallback`；`fetch_user_post_videos` 增加主备切换逻辑
- **配置**: `config.py` 中 `TikHubConfig` 新增 `fallback_endpoint` 字段（默认 `/api/v1/douyin/web/fetch_user_post_videos`）
- **测试**: `test_tikhub.py` 已更新使用新参数名 `max_cursor`/`count`
- **无 breaking change**: 对外接口签名不变，主接口仍为 APP v3
