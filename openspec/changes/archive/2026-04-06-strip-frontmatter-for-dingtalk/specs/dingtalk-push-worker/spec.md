## MODIFIED Requirements

### Requirement: 钉钉消息推送 handler
系统 SHALL 提供 `handle_dingtalk_push(task, config)` handler 函数，读取报告文件，移除 Obsidian YAML frontmatter 后通过钉钉 Webhook 推送到群聊，作为流水线终端阶段。

#### Scenario: 成功推送报告
- **WHEN** task.inputs 包含有效的 report_file 路径
- **AND** 报告文件存在且可读
- **THEN** 系统 SHALL 读取报告全文
- **AND** 移除报告顶部的 YAML frontmatter（`---` 包裹的块）
- **AND** 构造钉钉 Markdown 消息（title=视频标题，text=过滤后的报告正文）
- **AND** 使用加签方式调用 Webhook API
- **AND** 返回 `{"push_status": "ok"}`

#### Scenario: 报告不包含 frontmatter
- **WHEN** 报告文件内容不以 `---` 开头
- **THEN** 系统 SHALL 原样使用全文推送，不做任何内容修改

#### Scenario: 报告文件不存在
- **WHEN** task.inputs 中的 report_file 路径对应的文件不存在
- **THEN** 系统 SHALL 抛出 RuntimeError 说明文件不存在

#### Scenario: task.inputs 缺少 report_file
- **WHEN** task.inputs 中没有 report_file 键
- **THEN** 系统 SHALL 抛出 RuntimeError 说明缺少必要输入
