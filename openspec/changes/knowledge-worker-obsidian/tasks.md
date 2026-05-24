## 1. 配置模型

- [x] 1.1 在 `config.py` 中新增 `KnowledgeWorkerConfig`（pull_endpoint=5557, obsidian_vault, prompt, model）
- [x] 1.2 `AppConfig` 加入 `knowledge_worker` 字段

## 2. knowledge_worker 实现

- [x] 2.1 创建 `knowledge_worker.py`，实现 `handle_knowledge` handler
- [x] 2.2 内置默认知识提炼 Prompt（可配置覆盖）
- [x] 2.3 复用 `analyze_worker._call_llm_api` 调 LLM
- [x] 2.4 生成 Obsidian Markdown 笔记写入 `{vault}/00-Inbox/`

## 3. 集成

- [x] 3.1 `config.yaml` 新增 `knowledge_worker` 配置段
- [x] 3.2 `main.py` 启动列表加入 `hot_pulse.knowledge_worker`
- [x] 3.3 `config.yaml.example` 同步更新
- [ ] 3.4 飞书表格"状态"字段新增选项：`知识整理中`、`知识整理完成`、`知识整理失败`（手动在飞书 UI 中操作）

## 4. 验证

- [x] 4.1 编译验证
- [ ] 4.2 端到端：ingest 一条视频 → 确认 Obsidian inbox 出现笔记
- [ ] 4.3 确认飞书表格状态正确流转：`文字转写完成` → `知识整理中` → `知识整理完成`
