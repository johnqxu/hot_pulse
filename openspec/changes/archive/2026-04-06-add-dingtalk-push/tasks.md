## 1. 配置与集成

- [x] 1.1 在 config.py 中新增 DingTalkWorkerConfig 模型（继承 WorkerConfig，含 webhook_url、min_interval 字段）
- [x] 1.2 在 config.py 的 SecretConfig 中新增 dingtalk_secret 字段，AppConfig 中新增 dingtalk_worker 字段
- [x] 1.3 在 task_manager.py 的 STAGE_MAPPING 中新增 "dingtalk_push" 阶段配置（init_status="报告分析完成", finish_status="报告推送完成", fail_status="报告推送失败", next_type=None）
- [x] 1.4 在 task_manager.py 中将 analyze 阶段的 next_type 从 None 改为 "dingtalk_push"，新增 next_input_map={"report_file": "report_file"}
- [x] 1.5 在 worker_base.py 的 _get_worker_config cfg_map 中新增 "dingtalk_push" → config.dingtalk_worker 映射
- [x] 1.6 在 config.yaml 中新增 dingtalk_worker 配置段（pull/push endpoint、webhook_url、min_interval）
- [x] 1.7 在 .env.example 中新增 DINGTALK_SECRET 说明

## 2. 核心实现

- [x] 2.1 创建 src/hot_pulse/dingtalk_worker.py，实现钉钉 Webhook 加签函数 _sign_url（HMAC-SHA256）
- [x] 2.2 实现 _send_dingtalk_message 函数（构造 Markdown 消息 JSON、调用 Webhook、检查响应）
- [x] 2.3 实现流控逻辑（模块级 _last_send_time 变量，handler 内 sleep 等待）
- [x] 2.4 实现 handle_dingtalk_push handler（读取报告文件、调用发送、返回结果）
- [x] 2.5 实现 run_dingtalk_worker 入口和 __main__ CLI 启动逻辑
