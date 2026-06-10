## Purpose

知识整理 Worker（knowledge_worker）负责接收转写完成的 manual 任务，调用 LLM 将文本提炼为结构化知识笔记并写入 Obsidian inbox。

## ADDED Requirements

### Requirement: knowledge_worker handler

系统 SHALL 提供 `handle_knowledge(task, config)` handler，由 `pipeline.run_manual_pipeline()` 在 knowledge 阶段调用，读转写文本，调 LLM 生成知识笔记，写入 Obsidian vault。

#### Scenario: 成功生成知识笔记
- **WHEN** Task.inputs 包含 text_file 且文件存在
- **THEN** 系统 SHALL 读取转写文本，调用 LLM API（复用 `analyze_worker._call_llm_api`）
- **AND** 使用 `knowledge_worker` 配置的 prompt（空则用内置默认）
- **AND** 笔记保存为 `{obsidian_vault}/00-Inbox/{title}.md`
- **AND** 返回 `{"obsidian_note": 文件路径}`

#### Scenario: 笔记格式
- **WHEN** 生成知识笔记
- **THEN** 笔记 SHALL 包含 YAML frontmatter（title, source, creator, platform, domain, tags, created, status=inbox）
- **AND** 正文按「一句话总结、所属领域、关键概念、要点、行动计划、标签」六节输出

#### Scenario: text_file 不存在
- **WHEN** Task.inputs 中无 text_file 或文件不存在
- **THEN** 系统 SHALL 抛出 RuntimeError

### Requirement: KnowledgeWorkerConfig

系统 SHALL 提供 `KnowledgeWorkerConfig`，包含 `obsidian_vault`（默认 `D:\docs\Obsidian`）、`prompt`（空则用内置默认）、`model`（空则复用 analyze_worker.model）。

#### Scenario: 缺省值
- **WHEN** config.yaml 中未配置 knowledge_worker 段
- **THEN** obsidian_vault SHALL 默认为 `D:\docs\Obsidian`

### Requirement: Knowledge Handler 调用方式

`handle_knowledge(task, config)` SHALL 作为纯函数，由 `pipeline.run_manual_pipeline()` 在 knowledge 阶段调用。

#### Scenario: 被 pipeline 调用
- **WHEN** pipeline 执行 knowledge 阶段
- **THEN** 系统 SHALL 直接调用 `handle_knowledge(task, config)`
