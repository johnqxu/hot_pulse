## 1. StageConfig 状态链配置

- [x] 1.1 StageConfig 新增 init_status 和 finish_status 字段
- [x] 1.2 更新 STAGE_MAPPING，为四个阶段配置 init_status/finish_status

## 2. TaskManager 状态写入

- [x] 2.1 TaskManager.finish() 将 finish_status 写入飞书"状态"字段

## 3. FeishuClient 按状态查询

- [x] 3.1 实现 query_records_by_status(status, task_type) 方法，按飞书"状态"字段过滤记录并返回 Task 列表

## 4. Worker 启动恢复

- [x] 4.1 run_worker() 启动时查询 init_status 对应的历史任务，逐条处理后再进入 ZMQ 主循环
