## MODIFIED Requirements

### Requirement: Download Worker 主循环
系统 SHALL 提供 download worker，通过 `run_worker("download", handle_download)` 启动，handler 负责视频下载逻辑。

#### Scenario: 成功处理单个下载任务
- **WHEN** run_worker 调用 handle_download handler
- **THEN** handler SHALL 从 task.inputs["play_urls"] 获取下载地址列表
- **AND** 按顺序逐个尝试下载，首个成功即停止
- **AND** 返回 outputs={"video_file": 本地文件路径}
- **AND** run_worker 负责 start/finish/build_next/send 逻辑

#### Scenario: 所有下载地址均失败
- **WHEN** play_urls 中所有 URL 下载均失败
- **THEN** handler SHALL 抛出 RuntimeError
- **AND** run_worker 负责调用 TaskManager.fail()

#### Scenario: Worker 优雅关闭
- **WHEN** worker 进程收到中断信号（SIGINT/SIGTERM）
- **THEN** run_worker SHALL 完成当前任务的处理后关闭 ZMQ 连接

### Requirement: Download Worker 独立运行入口
系统 SHALL 支持通过 `python -m hot_pulse.download_worker` 独立启动 download worker。

#### Scenario: 以 CLI 方式运行
- **WHEN** 用户执行 `python -m hot_pulse.download_worker`
- **THEN** 系统 SHALL 调用 `run_worker("download", handle_download)`
