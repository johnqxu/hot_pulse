## 1. Task 模型修改

- [x] 1.1 修改 `task.py`：在 Task 模型"源信息"区域新增 `source: str = "subscription"` 字段

## 2. monitor 适配

- [x] 2.1 修改 `monitor.py` 中 `_send_zmq_task`：构造 Task 时显式传入 `source="subscription"`

## 3. 验证

- [x] 3.1 编译验证：`python -m py_compile src/hot_pulse/task.py src/hot_pulse/monitor.py`
- [x] 3.2 确认各 worker 启动不报错：依次启动 download/extract/transcribe/analyze worker，检查无 JSON 反序列化错误
