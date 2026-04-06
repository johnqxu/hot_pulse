## Context

流水线已完成 download → extract_audio → transcribe 三个阶段，转写文本以纯文本文件存储。analyze worker 是流水线最终阶段，将转写文本发送给 GLM-5.1 大模型进行财经内容分析，自动生成结构化投资分析报告。

报告格式参照用户现有 Obsidian 笔记模板，包含：YAML frontmatter、内容摘要、推荐板块、推荐个股（A股/港股）、风险提示、操作建议、标签。

运行环境：Windows 11，httpx 同步模式调用智谱 AI API。

## Goals / Non-Goals

**Goals:**
- 实现转写文本 → GLM API → 结构化分析报告的完整流程
- 报告格式与现有 Obsidian 模板一致（Markdown + YAML frontmatter）
- 模型名称可配置（默认 glm-5.1）
- API Key 通过 .env 管理，遵循项目敏感信息分离约定

**Non-Goals:**
- 不实现流式输出
- 不实现多模型对比分析
- 不实现报告模板自定义（固定为财经分析模板）
- 不实现报告内容的人工审核/修正流程

## Decisions

### 1. API 调用方式：httpx 直调 OpenAI 兼容接口

**选择**: 使用已有的 httpx 直接调用智谱 AI 的 OpenAI 兼容 API

**备选**:
- `zhipuai` 官方 SDK：多一层依赖，且项目已有 httpx
- `openai` SDK：额外依赖，仅用于兼容格式

**理由**: 智谱 AI API 兼容 OpenAI chat completions 格式（`/api/paas/v4/chat/completions`），项目已有 httpx 同步模式，无需引入新依赖。减少依赖链，与项目"成熟、轻量级"偏好一致。

### 2. 报告生成策略：单次 API 调用 + 结构化 prompt + 分隔符提取摘要

**选择**: 设计专用 system prompt，引导 GLM 按固定章节结构输出完整报告。报告第一行用分隔符包裹 10 字摘要，供代码提取用于文件名。

**格式**: GLM 响应首行输出 `<<<SUMMARY>>>不超过10字的摘要<<<END>>>`，后续为报告正文（从 `### 1. 内容摘要` 开始）。代码解析首行提取摘要，剩余部分作为报告正文。

**理由**: 单次 API 调用同时获取摘要和报告正文，避免额外调用开销。分隔符格式简单可靠，易于正则解析。GLM-5.1 具备良好的指令遵循能力，能稳定输出指定格式。

### 3. 报告输出格式：Markdown + YAML frontmatter

**选择**: 报告文件为 `.md` 格式，头部包含 YAML frontmatter（video_id、creator、title 等元数据），正文为结构化 Markdown

**理由**: 与用户现有 Obsidian 笔记格式完全兼容，无需额外格式转换。frontmatter 中的元数据从 Task 对象中提取，不需要 LLM 生成。

### 4. 文件命名：`{date}-{creator}-{摘要}.md`

**选择**: 报告文件命名为 `{YYYYMMDD}-{creator}-{摘要}.md`，其中摘要由 GLM 从转写文本中提炼，不超过 10 个汉字

**理由**: 与用户现有 Obsidian 笔记命名规则一致（如 `20260404-口罩哥-地缘博弈下的军工重估.md`），便于在 Obsidian 中浏览和检索。使用 LLM 提炼摘要代替视频标题，避免标题过长、含特殊字符或与内容不匹配的问题。摘要通过额外一次轻量 API 调用获取，或在主分析 prompt 中一并要求输出。

## Risks / Trade-offs

- **[GLM API 限流/超时]** → httpx 设置 120s 超时；单次调用失败由 worker_base 框架重试（状态回退到 init_status）
- **[长文本超出 token 限制]** → transcribe 输出的文本通常为几分钟视频的转写，token 量可控。若超长则截断并记录警告
- **[报告质量不稳定]** → 通过精细的 system prompt 和 few-shot 示例约束输出格式；用户可通过调整 model 配置切换更强模型
- **[摘要提取失败]** → 若首行无分隔符，使用视频标题截断 10 字作为兜底文件名
- **[文件名特殊字符]** → 摘要结果移除不适合文件系统的字符（`/\:*?"<>|`）
