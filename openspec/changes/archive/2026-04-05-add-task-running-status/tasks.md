## 1. StageConfig 配置

- [x] 1.1 StageConfig 新增 running_status 和 fail_status 字段
- [x] 1.2 更新 STAGE_MAPPING， 为四个阶段配置 running_status、fail_status，修正 analyze 的 finish_status 为"报告分析完成"

- [x] 2.1 TaskManager.start() 将 running_status 写入飞书"状态"字段
- [x] 2.2 TaskManager.fail() 将 fail_status 写入飞书"状态"字段（替代硬编码"失败")
