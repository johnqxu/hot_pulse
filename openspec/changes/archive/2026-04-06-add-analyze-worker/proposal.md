## Why

流水线已完成 download → extract_audio → transcribe 三个阶段，转写文本以纯文本文件存储在本地。现需实现 analyze worker，将转写文本发送给 GLM 大模型进行财经内容分析，自动生成结构化投资分析报告，替代人工逐条观看视频并手写报告的低效流程。

## What Changes

- 新建 `analyze_worker.py`，读取转写文本，调用智谱 AI GLM-5.1 API 生成结构化分析报告
- 报告格式参照现有 Obsidian 笔记模板：内容摘要、推荐板块、推荐个股（A股/港股）、风险提示、操作建议、标签
- 报告输出为 Markdown 文件，保存到 `report_dir`，同时写入飞书多维表格
- `.env` 新增 `ZHIPU_API_KEY` 敏感凭证
- `AnalyzeWorkerConfig` 新增 `model` 配置项（默认 `glm-5.1`）

## Capabilities

### New Capabilities
- `analyze-worker`: 使用 GLM API 对转写文本进行财经内容分析，生成结构化投资分析报告（Markdown 格式）

### Modified Capabilities
- `config-management`: AnalyzeWorkerConfig 新增 model、prompt 字段；SecretConfig 新增可选 zhipu_api_key

## Impact

- **新增依赖**: 无（使用已有 httpx 直调智谱 AI OpenAI 兼容接口）
- **修改文件**: `config.py`（配置模型）、`config.yaml`（analyze_worker 配置段）、`.env` / `.env.example`（新增 ZHIPU_API_KEY）
- **流水线位置**: transcribe(5554) → **analyze(5555)**（最终阶段）
- **外部服务**: 智谱 AI 开放平台 API（open.bigmodel.cn）
