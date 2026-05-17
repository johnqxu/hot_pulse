## 1. 配置模型修改

- [x] 1.1 修改 `config.py` 中 `TikHubConfig`：新增 `fallback_endpoint` 字段（默认 `/api/v1/douyin/web/fetch_user_post_videos`）

## 2. TikHub 客户端重构

- [x] 2.1 修正 `_do_fetch` 的参数名：`cursor` → `max_cursor`，`max_count` → `count`，新增 `sort_type=0`
- [x] 2.2 拆分 `_do_fetch` 为 `_do_fetch_primary`（APP v3，参数含 `sort_type`）和 `_do_fetch_fallback`（Web，参数含 `filter_type`），两台函数共享视频解析逻辑
- [x] 2.3 修改 `fetch_user_post_videos`：主接口 3 次重试失败后调用备用接口（不重试），备用失败则抛异常；`fallback_endpoint` 为空则跳过备用

## 3. 配置文件同步

- [x] 3.1 更新 `config.yaml.example` 中 `tikhub` 段，新增 `fallback_endpoint` 字段及注释
- [x] 3.2 更新 `config.yaml` 中 `tikhub` 段，新增 `fallback_endpoint` 字段

## 4. 验证

- [ ] 4.1 运行 `test_tikhub.py` 测试主接口（确认参数名修正后正常返回）
- [ ] 4.2 运行 `test_tikhub.py` 测试备用接口降级（临时改 endpoint 为空验证 fallback 触发）
