## 1. Task 数据模型

- [x] 1.1 新增 `src/hot_pulse/task.py`：定义 Task Pydantic Model（task_id, task_type, video_id, creator, title, platform, feishu_record_id, inputs, outputs, status, error, created_at, updated_at），提供 `model_dump_json()` 和 `model_validate_json()` 序列化支持

## 2. 阶段配置映射

- [x] 2.1 在 `src/hot_pulse/task_manager.py` 中定义 StageConfig dataclass 和 STAGE_MAPPING 字典，声明 download/extract_audio/transcribe/analyze 四个阶段的飞书字段映射、output_map、next_type、next_input_map

## 3. TaskManager 能力层

- [x] 3.1 在 `src/hot_pulse/task_manager.py` 中实现 TaskManager 类：start()（更新飞书开始时间+状态+日志）、finish()（更新飞书结束时间+outputs+日志）、fail()（更新飞书错误状态+日志）、build_next()（构造下一阶段 Task）

## 4. 飞书客户端扩展

- [x] 4.1 修改 `src/hot_pulse/feishu.py`：create_records 返回 record_id 列表；新增 update_record(record_id, fields) 方法按 record_id 更新单条记录

## 5. ZMQ 客户端扩展

- [x] 5.1 修改 `src/hot_pulse/zmq_client.py`：ZmqPublisher 新增 send_task(task) 方法；新增 ZmqConsumer 类（PULL socket, bind, recv_task, close）

## 6. Monitor 集成

- [x] 6.1 修改 `src/hot_pulse/monitor.py`：create_records 后捕获 record_id，构造 Task 对象（task_type="download"），通过 ZMQ 发送 Task 替代原手写 dict

## 7. 验证

- [x] 7.1 运行 `python -m hot_pulse.monitor`，配合 PULL 测试脚本验证收到的消息是合法的 Task JSON 格式
