## 1. 依赖配置

- [x] 1.1 在 `pyproject.toml` 中添加 `yt-dlp` 依赖

## 2. ingest.py CLI 实现

- [x] 2.1 创建 `src/hot_pulse/ingest.py`，实现 argparse 参数解析（--type, --platform, --url, --title, --notes）
- [x] 2.2 实现 `_resolve_url(url)` → subprocess 调用 `yt-dlp --dump-json`，解析 JSON 提取直链、title、video_id
- [x] 2.3 实现 `_build_task()` → 构造 Task(source="manual", inputs.play_urls=[直链], inputs.notes=args.notes)
- [x] 2.4 实现 `_push_and_exit()` → ZmqPublisher 推送 Task 到 5551，stdout 输出 task_id JSON，退出

## 3. 验证

- [x] 3.1 yt-dlp 功能验证：`yt-dlp --dump-json "https://www.bilibili.com/video/BV1xxx"` 确认能获取 JSON
- [x] 3.2 端到端验证：执行 `python -m hot_pulse ingest --type video --platform bilibili --url "..." --title "测试"`，确认 download_worker 收到 Task 并开始下载
