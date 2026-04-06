## 1. TikHub 数据提取

- [x] 1.1 修改 `src/hot_pulse/tikhub.py`：从 `item.video.play_addr_h264.url_list` 提取播放地址数组，降级使用 `video.play_addr.url_list`，存入 `VideoInfo` 的新字段 `play_urls`
- [x] 1.2 修改 `src/hot_pulse/models.py`：`VideoInfo` 新增 `play_urls` 字段（`list[str]`），`build_record` 将 `play_urls` 以 JSON 字符串写入"视频链接"

## 2. 字段格式调整

- [x] 2.1 修改 `src/hot_pulse/models.py`：将"视频链接"从超链接格式 (`_URL_FIELDS`) 移除，改为纯文本存储 JSON 字符串

## 3. 验证

- [x] 3.1 运行 `python -m hot_pulse.monitor` 确认飞书表格"视频链接"字段写入的是 JSON 数组格式
