## 1. 配置与基础设施

- [x] 1.1 修改 `src/hot_pulse/config.py`：新增 `PatrolWorkerConfig`（interval_minutes=60, zombie_threshold_minutes=90），添加到 `AppConfig`
- [x] 1.2 修改 `config.yaml`：新增 `patrol_worker` 配置段

## 2. 核心实现

- [x] 2.1 创建 `src/hot_pulse/patrol_worker.py`：构建 STAGE_REVERSE 反向映射表（从 running_status/fail_status 反查 task_type 和 init_status）
- [x] 2.2 实现飞书查询逻辑：对每种 running_status 和 fail_status 分别查询飞书表格
- [x] 2.3 实现僵尸检测：检查 start_field 时间戳，超过 zombie_threshold_minutes 的判定为僵尸
- [x] 2.4 实现回退逻辑：将飞书状态更新为 init_status
- [x] 2.5 实现 ZMQ 路由推送：为每种 task_type 创建 PUSH socket，按 task_type 路由发送 Task
- [x] 2.6 实现主循环：定时巡检 + 信号处理 + 优雅关闭
- [x] 2.7 添加 `if __name__ == "__main__"` CLI 入口

## 3. 集成

- [x] 3.1 修改 `src/hot_pulse/main.py`：在 _WORKERS 列表中添加 patrol_worker 子进程
- [x] 3.2 修改 `src/hot_pulse/worker_base.py`：patrol_worker 不使用 run_worker() 基座，无需修改 worker_base

## 4. 验证

- [x] 4.1 确认 patrol_worker 可独立运行（import 验证通过，STAGE_REVERSE 10 条映射正确）
- [x] 4.2 确认 main.py 启动时包含 patrol_worker（_WORKERS 列表已包含 hot_pulse.patrol_worker）
