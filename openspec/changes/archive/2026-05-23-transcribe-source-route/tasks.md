## 1. STAGE_MAPPING 扩展

- [x] 1.1 在 `task_manager.py` 的 `STAGE_MAPPING` 中新增 `knowledge` 阶段配置

## 2. build_next 分流

- [x] 2.1 修改 `build_next`：transcribe 阶段 source="manual" 时 next_type="knowledge"

## 3. 验证

- [x] 3.1 编译验证：`python -m py_compile src/hot_pulse/task_manager.py`
