## Why

当前 `_download_video()` 按 play_urls 列表原始顺序依次尝试下载，所有 URL 被同等对待。实际中不同 CDN 域名的下载速度和稳定性差异很大（如 `*.amemv.com` 通常更快），需要在配置中定义域名优先级，优先从高优先级地址下载，提高下载成功率。

## What Changes

- 修改 `config.yaml` 和 `DownloadWorkerConfig`：新增 `url_priority` 配置项，映射域名模式到优先级数值（数值越高越优先）
- 修改 `download_worker.py`：`_download_video()` 根据 url_priority 配置对 play_urls 按优先级排序后再尝试下载

## Capabilities

### New Capabilities

（无）

### Modified Capabilities
- `download-worker`: 下载前按域名优先级排序 play_urls
- `config-management`: DownloadWorkerConfig 新增 url_priority 配置

## Impact

- 修改文件：`config.py`、`download_worker.py`、`config.yaml`
- 无新文件、无新依赖
