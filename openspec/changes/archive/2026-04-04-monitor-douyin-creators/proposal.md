## Why

需要一个自动化工具定时监控抖音创作者的新作品发布情况，并将发现的新作品记录到飞书多维表格中，作为后续内容处理流水线（下载、转写、分析）的第一步。当前手动跟踪效率低下且容易遗漏。

## What Changes

- 新增独立的内容监控模块 `monitor.py`，定时轮询 TikHub API 获取指定创作者的最新视频列表
- 新增 TikHub API 客户端模块 `tikhub.py`，封装抖音视频列表查询接口
- 新增飞书多维表格客户端模块 `feishu.py`，实现记录查询与写入
- 新增配置加载模块 `config.py`，支持 YAML 配置 + `.env` 敏感信息分离
- 新增数据模型定义 `models.py`，定义视频记录与表格字段映射
- 通过飞书多维表格查询已有记录实现去重，无需本地数据库
- 模块既可作为独立 CLI 运行（供 OpenClaw Cron 调度），也可被 `main.py`（预留）import 编排

## Capabilities

### New Capabilities
- `douyin-monitor`: 抖音创作者视频监控与飞书记录同步，包括 TikHub 数据拉取、飞书多维表格读写、新作品检测与记录写入
- `config-management`: 项目配置管理，YAML 配置与 .env 敏感信息分离加载

### Modified Capabilities
<!-- 无现有能力需要修改 -->

## Impact

- 新增项目依赖：httpx, pydantic-settings, python-dotenv, loguru, pyyaml
- 外部服务依赖：TikHub API（抖音数据）、飞书开放平台 API（多维表格读写）
- 需要 TikHub API Key、飞书应用 App ID 和 App Secret
- 飞书多维表格需提前创建并配置相应字段
