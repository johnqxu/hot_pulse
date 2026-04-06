## 1. 项目初始化

- [x] 1.1 创建项目结构：`src/hot_pulse/` 及 `__init__.py`，创建 `pyproject.toml` 并声明依赖（httpx, pydantic-settings, python-dotenv, loguru, pyyaml）
- [x] 1.2 创建 `.env.example` 列出所需环境变量（TIKHUB_API_KEY, FEISHU_APP_ID, FEISHU_APP_SECRET），创建 `.gitignore` 排除 `.env`

## 2. 配置模块

- [x] 2.1 创建 `src/hot_pulse/config.py`：使用 pydantic-settings 定义 TikHub、飞书多维表格、创作者、调度等配置模型及根配置 AppConfig
- [x] 2.2 实现 YAML 配置加载（从 `config.yaml`）+ `.env` 敏感信息合并，带校验和清晰的错误提示

## 3. 数据模型

- [x] 3.1 创建 `src/hot_pulse/models.py`：定义 VideoRecord 数据类/模型，包含所有飞书表格字段，定义字段映射常量（任务名、优先级、状态等）

## 4. TikHub API 客户端

- [x] 4.1 创建 `src/hot_pulse/tikhub.py`：使用 httpx 实现 TikHub 客户端类，包含 API Key 认证头和 `fetch_user_post_videos` 方法，调用 `/api/v1/douyin/app/v3/fetch_user_post_videos`
- [x] 4.2 添加重试机制（最多 3 次，指数退避）和错误处理

## 5. 飞书多维表格客户端

- [x] 5.1 创建 `src/hot_pulse/feishu.py`：实现飞书客户端类，包含通过 app_id/app_secret 获取 tenant_access_token 的逻辑
- [x] 5.2 实现 `query_video_ids` 方法：按博主名称筛选，查询飞书表格中已有的视频 ID
- [x] 5.3 实现 `create_records` 方法：批量写入新视频记录到飞书表格，按字段映射填充（任务名、优先级、状态、任务类型等）

## 6. 监控编排

- [x] 6.1 创建 `src/hot_pulse/monitor.py`：实现 `run_monitor()` 函数，遍历所有创作者，从 TikHub 拉取视频，查询飞书已有记录，计算差集，写入新记录
- [x] 6.2 添加 `__main__` 块支持 CLI 执行（`python -m hot_pulse.monitor`），输出结果摘要日志

## 7. 配置文件与验证

- [x] 7.1 创建 `config.yaml` 模板，包含 TikHub、飞书表格、创作者列表、调度等配置段
- [x] 7.2 端到端验证：运行 `python -m hot_pulse.monitor`，确认 TikHub 连接、飞书查询、记录写入均正常
