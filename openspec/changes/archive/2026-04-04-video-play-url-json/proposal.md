## Why

当前监控模块将 TikHub 返回的 `share_url`（分享链接）写入飞书"视频链接"字段，但该链接是网页分享地址，不适合后续视频下载阶段直接使用。需要将实际的视频播放地址（`play_addr_h264.url_list`）存入飞书，为阶段②视频下载提供直接可用的下载地址。

## What Changes

- 修改 `tikhub.py` 的数据解析逻辑：从 `aweme_list[].video.play_addr_h264.url_list` 提取视频播放地址数组
- 修改 `models.py` 的字段映射：将"视频链接"字段的值从单个分享链接改为 `play_addr_h264.url_list` 的 JSON 字符串
- 飞书"视频链接"字段存储格式从超链接（`{"link": url, "text": url}`）变更为 JSON 文本字符串

## Capabilities

### New Capabilities
<!-- 无新增能力 -->

### Modified Capabilities
- `douyin-monitor`: 视频链接字段的数据来源从 share_url 变更为 play_addr_h264.url_list JSON 数组

## Impact

- 飞书表格中"视频链接"字段的内容格式变更（从单条 URL 变为 JSON 数组字符串）
- 飞书表格字段类型需从"超链接"(type=15) 改为"文本"(type=1)，因为 JSON 字符串不符合超链接格式
- 已写入的历史记录中"视频链接"字段格式与新格式不一致，需手动处理或接受差异
