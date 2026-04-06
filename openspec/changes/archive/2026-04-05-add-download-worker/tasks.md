## 1. 配置扩展

- [x] 1.1 在 `src/hot_pulse/config.py` 中新增 `DownloadWorkerConfig`（pull_endpoint, push_endpoint, download_dir），添加到 AppConfig

## 2. 下载逻辑

- [x] 2.1 在 `src/hot_pulse/download_worker.py` 中实现 `_download_video()` 函数：遍历 play_urls，使用 httpx 流式下载到 `{download_dir}/{video_id}.mp4`

## 3. Worker 主循环

- [x] 3.1 在 `src/hot_pulse/download_worker.py` 中实现 `run_download_worker()` 函数：初始化 ZmqConsumer/ZmqPublisher/TaskManager，循环 recv_task → start → download → finish → build_next → send_task
- [x] 3.2 添加 `if __name__ == "__main__"` 入口和信号处理（优雅关闭）

## 4. 配置文件

- [x] 4.1 在 `config.yaml` 中添加 `download_worker` 配置段

## 5. 验证

- [x] 5.1 启动 download worker，配合 monitor 发送测试 Task，验证下载成功、飞书更新、下游 Task 发送
