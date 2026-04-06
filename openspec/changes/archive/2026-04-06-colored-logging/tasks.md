## 1. 修改日志格式

- [x] 1.1 修改 `src/hot_pulse/worker_base.py`：在 `run_worker()` 中根据 task_type 选择颜色，在 `logger.add()` 的 format 中嵌入颜色标签和 `[task_type]` 前缀
- [x] 1.2 修改 `src/hot_pulse/main.py`：主进程日志使用绿色 `[main]` 前缀
- [x] 1.3 修改各 worker 的 `if __name__ == "__main__"` 入口：移除各自的 logger 配置，由 worker_base 统一管理；monitor 独立运行使用 `<bold>[monitor]</bold>` 前缀

## 2. 验证

- [x] 2.1 确认各进程日志颜色正确显示，前缀标识清晰
