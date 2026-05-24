## Why

Manual 提交的 video 已完成 transcribe→knowledge 阶段路由，但 knowledge_worker 尚未实现。需要新增知识整理 Worker，将转写文本通过 LLM 提炼为结构化知识笔记，写入 Obsidian vault 的 inbox。

## What Changes

- 新增 `knowledge_worker.py`，pull ZMQ 5557，读转写文本，调 LLM 生成知识笔记
- 新增 `KnowledgeWorkerConfig` 配置模型（pull_endpoint, obsidian_vault, prompt 等）
- `config.yaml` 新增 `knowledge_worker` 配置段
- `main.py` 启动列表加入 `knowledge_worker`
- 内置默认知识提炼 Prompt（可配置覆盖），AI 自动标注领域和 tags
- 笔记输出到 `{obsidian_vault}/00-Inbox/{title}.md`，格式含 frontmatter + 结构化章节

## Capabilities

### New Capabilities

- `knowledge-worker-obsidian`: 通用知识整理 Worker，从转写文本中提炼结构化笔记写入 Obsidian

### Modified Capabilities

（无）

## Impact

- **代码**: 新增 `knowledge_worker.py`（~120 行）、`config.py` 加 `KnowledgeWorkerConfig`、`main.py` 加 1 行
- **配置**: `config.yaml` 新增 `knowledge_worker` 段
- **管道**: manual 管道的终端阶段，`next_type=None`
