## 1. 依赖配置

- [x] 1.1 在 `pyproject.toml` 中添加 `pycryptodome` 依赖

## 2. TikHubClient 扩展

- [x] 2.1 在 `tikhub.py` 中新增 `fetch_weixin_video_detail(export_id)` 方法，调 TikHub API（参数 `exportId`），按实际 JSON 路径返回视频详情

## 3. ingest CLI 适配

- [x] 3.1 `ingest.py` 中 `--platform` 的 `choices` 从 `["bilibili"]` 改为 `["bilibili", "weixin"]`
- [x] 3.2 新增 `_resolve_weixin_url(url)` — 从 sph 链接提取 exportId，调 TikHubClient 获取元信息（按实际 JSON 路径提取字段）
- [x] 3.3 `main()` 中根据 platform 路由：bilibili 走 yt-dlp，weixin 走 TikHub API
- [x] 3.4 Task.inputs 中携带 `encrypted_url`、`url_token`、`decode_key` 供 download_worker 使用

## 4. download_worker 解密

- [x] 4.1 新增 `_download_via_tikhub_weixin(task, config)` — 拼接完整 URL → 下载加密视频 → AES 解密（模式需验证） → 输出 mp4
- [x] 4.2 `handle_download()` 中的 manual 分支根据 platform 路由：bilibili 走 yt-dlp，weixin 走 TikHub 解密

## 5. OpenClaw Skill 更新

- [x] 5.1 更新 `skills/hot-pulse-ingest.md` — 新增微信视频号链接的触发条件和示例

## 6. 验证

- [x] 6.1 编译验证
- [ ] 6.2 先单独验证 TikHub API + 解密流程（用真实 sph 链接测试）
- [ ] 6.3 端到端：`python -m hot_pulse ingest --type video --platform weixin --url "..."` 确认完整管道
