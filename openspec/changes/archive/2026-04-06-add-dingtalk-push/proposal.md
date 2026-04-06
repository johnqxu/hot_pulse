## Why

分析报告生成后保存在本地 Obsidian 仓库，团队成员无法及时获知新报告内容。需要将报告自动推送到钉钉群，让团队第一时间看到分析结果。

## What Changes

- 新增 `dingtalk_push` worker 作为流水线末尾阶段，紧接 analyze 之后
- 通过钉钉自定义机器人 Webhook 推送 Markdown 格式报告到群聊
- 使用加签（HMAC-SHA256）方式认证
- 实现流控：每条消息间隔至少 2 分钟，避免触发钉钉频率限制
- 报告完整推送（不超过 10000 字），无需截断
- 启动时从飞书表格恢复待推送任务

## Capabilities

### New Capabilities
- `dingtalk-push-worker`: 钉钉消息推送 worker，包含 Webhook 调用、加签认证、流控、报告格式化

### Modified Capabilities
- `config-management`: 新增 DingTalkWorkerConfig 配置模型和 DINGTALK_SECRET 环境变量
- `worker-base`: 新增 dingtalk_push worker 配置映射
- `task-model` 无需求变更（现有 Task 模型已满足）

## Impact

- 新文件：`src/hot_pulse/dingtalk_worker.py`
- 修改文件：`config.py`、`worker_base.py`、`task_manager.py`、`config.yaml`、`.env.example`
- 依赖：无新依赖（使用标准库 hmac/hashlib/time + httpx）
- ZMQ 端口链扩展：5555→5556（dingtalk_push pull from 5555）
