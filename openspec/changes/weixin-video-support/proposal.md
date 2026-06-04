## Why

当前 ingest CLI 和 download_worker 仅支持 B站视频的手动提交和处理。用户也有微信视频号的内容需要纳入知识库。yt-dlp 不支持微信视频号，但 TikHub API 已提供微信视频号视频详情接口，可通过 API 获取加密视频并解密后走标准管道。

## What Changes

- `ingest.py`: `--platform` 新增 `weixin` 选项，TikHub API 解析视频元信息（替代 yt-dlp）
- `download_worker.py`: 新增 `_download_via_tikhub_weixin()` 函数，调 TikHub API 下载加密视频 + 解密
- `tikhub.py` `TikHubClient`: 新增 `fetch_weixin_video_detail()` 方法
- `skills/hot-pulse-ingest.md`: 新增微信视频号触发条件

## Capabilities

### New Capabilities

- `weixin-video-support`: 微信视频号内容通过 TikHub API 接入 Hot Pulse 管道

### Modified Capabilities

- `ingest-cli`: `--platform` 从 `["bilibili"]` 扩展为 `["bilibili", "weixin"]`
- `tikhub-api-fallback`: TikHubClient 新增微信视频号接口

## Impact

- **代码**: `ingest.py`（1 行改）、`download_worker.py`（~40 行新函数）、`tikhub.py`（~30 行新方法）
- **依赖**: 无新增（TikHub API 已有认证），需安装解密工具依赖
- **配置**: 无需改 config.yaml
- **OpenClaw Skill**: `skills/hot-pulse-ingest.md` 更新
