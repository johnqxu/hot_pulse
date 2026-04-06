## Context

analyze worker 生成的报告以 Obsidian 兼容格式保存，顶部包含 YAML frontmatter（`---` 包裹的元数据块）。dingtalk_worker 当前直接读取全文推送，frontmatter 在钉钉 Markdown 渲染中显示为原始文本，影响阅读体验。

## Goals / Non-Goals

**Goals:**
- 推送前自动检测并移除报告顶部的 YAML frontmatter
- 本地保存的报告文件不受影响

**Non-Goals:**
- 不修改 analyze worker 的报告生成逻辑
- 不增加配置项（frontmatter 格式固定，无需配置化）

## Decisions

### 使用正则匹配移除 frontmatter

**选择**：在 dingtalk_worker 中增加 `_strip_frontmatter(text)` 函数，用正则 `^---\n.*?\n---\n` 匹配并移除。

**替代方案**：逐行解析（找到首行 `---`，再找第二个 `---`，截取之后的内容）。

**理由**：正则简洁且性能足够（报告 < 10000 字），符合项目中 analyze_worker 已有的正则模式风格（如 SUMMARY_PATTERN）。

### 放置位置

**选择**：在 `handle_dingtalk_push` 中读取文件后、调用 `_send_dingtalk_message` 前调用。

**理由**：保持关注点分离——发送函数只负责构造消息和 HTTP 调用，内容预处理由 handler 负责。

## Risks / Trade-offs

- **[frontmatter 格式变化]** → 如果 analyze_worker 修改了报告格式（如不再包含 frontmatter），正则不会匹配到任何内容，全文原样推送，行为安全。
