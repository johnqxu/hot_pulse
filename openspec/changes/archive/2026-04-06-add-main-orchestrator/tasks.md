## 1. 创建 main.py 主进程编排器

- [x] 1.1 创建 `src/hot_pulse/main.py`，实现子进程启动逻辑：按顺序通过 `subprocess.Popen` 启动 5 个 worker（download → extract_audio → transcribe → analyze → dingtalk_push），每个使用 `sys.executable -m hot_pulse.xxx_worker` 命令
- [x] 1.2 实现 worker 启动失败处理：如果某个 worker 子进程启动后立即退出（非 0 返回码），记录错误日志，终止已启动的其他子进程，主进程退出
- [x] 1.3 实现 30 秒等待延迟：所有 worker 启动完成后 `time.sleep(30)` 再进入 monitor 调度循环
- [x] 1.4 实现 monitor 定时调度循环：检查时间窗口（07:00-22:00），在窗口内调用 `run_monitor()`，异常时记录日志继续循环，每次循环后 `time.sleep(interval_minutes * 60)`
- [x] 1.5 实现信号处理：捕获 SIGINT/SIGTERM，设置 `shutting_down` 标志，主循环退出后依次向子进程发送 `terminate()`，等待 10 秒超时后 `kill()`
- [x] 1.6 添加 `if __name__ == "__main__"` 入口和日志配置

## 2. 验证

- [x] 2.1 确认各 worker 和 monitor 保持独立运行能力（`python -m hot_pulse.xxx_worker`、`python -m hot_pulse.monitor` 不受影响）
- [x] 2.2 确认 main.py 可一键启动所有 worker 并进入 monitor 调度循环
