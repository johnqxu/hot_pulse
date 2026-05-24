## Context

Manual 管道：ingest → download(yt-dlp) → extract_audio → transcribe → knowledge → Obsidian。knowledge_worker 是这个管道终端阶段。

## Goals / Non-Goals

**Goals:**
- 实现 knowledge_worker，pull ZMQ 5557，读转写文本，调 LLM 生成知识笔记写入 Obsidian
- Prompt 可配置，内置默认知识提炼 Prompt
- AI 自动标注领域（domain）和 tags
- 笔记写入 `{vault}/00-Inbox/`，文件名来自 title

**Non-Goals:**
- 不处理阶段 2（手动回顾加工）
- 不做钉钉推送

## Decisions

### 1. 配置模型

```python
class KnowledgeWorkerConfig(WorkerConfig):
    pull_endpoint: str = "tcp://127.0.0.1:5557"
    obsidian_vault: str = r"D:\docs\Obsidian"
    model: str = ""           # 空则复用 analyze_worker 的 model
    prompt: str = ""          # 空则用内置默认
```

`model` 为空时复用 `analyze_worker.model`，保持 LLM 配置统一。

### 2. 内置默认 Prompt

方向是"通用知识提炼"，和财经分析的"投资建议"完全不同：

```
你是一位专业的知识管理助手。请根据以下视频转写文本，提炼结构化知识笔记。

必须严格按以下格式输出：

## 一句话总结
## 所属领域
## 关键概念
## 要点
## 行动计划
## 标签
```

### 3. Worker 与 analyze_worker 复用 LLM 调用

`knowledge_worker.py` 不重复实现 `_call_llm_api`，直接从 `analyze_worker` import 复用。

### 4. 笔记文件格式

```markdown
---
title: "..."
source: "..."
creator: "..."
platform: "bilibili"
domain: "AI/深度学习"
tags: [AI, Transformer, Attention]
created: 2026-05-24
status: inbox
---

# {title}

## 一句话总结
...

## 所属领域
**AI / 深度学习 / 自然语言处理**

## 关键概念
- **概念**: 解释
...

## 要点
1. ...

## 行动计划
- [ ] ...

## 标签
#AI #Transformer
```

全部由 LLM 生成，frontmatter 里的结构化字段由 handler 组装。

## Risks / Trade-offs

- **[风险] LLM 输出的 Markdown 格式不稳定**：有时不按模板输出 → **缓解**：frontmatter 字段由代码组装，不依赖 LLM；正文部分只做宽松校验
