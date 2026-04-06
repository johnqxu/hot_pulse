## 1. 配置模型

- [x] 1.1 DownloadWorkerConfig 新增 url_priority 字段（dict[str, int]，默认空 dict）
- [x] 1.2 config.yaml 添加 url_priority 默认配置

## 2. 下载排序逻辑

- [x] 2.1 实现 URL 域名提取和优先级匹配函数（支持 `*` 通配符前缀）
- [x] 2.2 修改 `_download_video()` 使用 url_priority 对 play_urls 排序后再下载
