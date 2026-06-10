## Purpose

Analyze worker 负责接收文字转写完成的任务，调用 OpenAI 兼容的 LLM API 对转写文本进行财经内容分析，生成结构化分析报告并保存为 Markdown 文件。

## Requirements

### Requirement: analyze worker handler
系统 SHALL 提供 analyze worker 的 handler 函数，从 Task.inputs 中获取 text_file，读取转写文本，调用 OpenAI 兼容的 LLM API 生成财经内容分析报告。

#### Scenario: 成功生成分析报告
- **WHEN** Task.inputs 包含有效的 text_file 路径
- **THEN** 系统 SHALL 读取转写文本内容
- **AND** 使用配置中指定的 openai_base_url、openai_api_key 和 model 调用 LLM API
- **AND** 将生成的报告保存为 `{report_dir}/{YYYYMMDD}-{creator}-{摘要}.md`
- **AND** 报告文件包含 YAML frontmatter（video_id, platform, creator, title, create_time, analysis_time, tags）
- **AND** 返回 {"report_file": report_file_path}

#### Scenario: text_file 不存在
- **WHEN** Task.inputs 中无 text_file
- **THEN** 系统 SHALL 抛出 RuntimeError

#### Scenario: 转写文本文件在磁盘上不存在
- **WHEN** text_file 指向的文件在磁盘上不存在
- **THEN** 系统 SHALL 抛出 RuntimeError

### Requirement: LLM API 调用
系统 SHALL 使用 httpx 同步模式调用 OpenAI 兼容接口，接口地址和认证信息由配置驱动。将转写文本作为 user message 发送，搭配专用 system prompt 引导模型输出结构化分析报告。

#### Scenario: 正常 API 调用
- **WHEN** 发送分析请求到 LLM API
- **THEN** 系统 SHALL 使用 POST 方法调用 `{openai_base_url}/chat/completions`
- **AND** 请求头包含 `Authorization: Bearer {openai_api_key}`
- **AND** 请求体包含 model、messages（system prompt + user message）、temperature 参数
- **AND** 若配置了 reasoning_effort，SHALL 在请求体顶层包含该字段
- **AND** 若配置了 extra_body，SHALL 将其键值对合并到请求体
- **AND** 设置 httpx 超时为 300 秒

#### Scenario: API 调用失败
- **WHEN** LLM API 返回非 200 状态码或网络异常
- **THEN** 系统 SHALL 抛出包含状态码和错误信息的异常

#### Scenario: API 响应解析
- **WHEN** LLM API 返回 200 状态码
- **THEN** 系统 SHALL 从响应 JSON 的 `choices[0].message.content` 中提取完整响应文本
- **AND** 系统 SHALL 解析首行的 `<<<SUMMARY>>>...<<<END>>>` 标记提取 10 字摘要用于文件名
- **AND** 剩余行作为报告正文

### Requirement: 报告格式
系统 SHALL 生成的分析报告包含以下固定章节结构：内容摘要、推荐板块、推荐个股（A股/港股）、风险提示、操作建议、标签。

#### Scenario: 报告包含完整章节
- **WHEN** LLM 成功返回分析内容
- **THEN** 报告 SHALL 包含 YAML frontmatter 和以下章节：内容摘要、推荐板块、推荐个股、风险提示、操作建议、标签
- **AND** frontmatter 中的 video_id、creator、title 从 Task 对象获取
- **AND** analysis_time 使用当前时间自动填充

#### Scenario: 文件名生成
- **WHEN** 生成报告文件名
- **THEN** 系统 SHALL 使用格式 `{YYYYMMDD}-{creator}-{摘要}.md`
- **AND** 摘要 SHALL 由 LLM 从响应首行分隔符 `<<<SUMMARY>>>...<<<END>>>` 中提取，不超过 10 个汉字
- **AND** 文件名中的摘要 SHALL 移除不适合文件系统的字符（`/\:*?"<>|`）

#### Scenario: 摘要提取失败兜底
- **WHEN** LLM 响应首行不包含分隔符标记
- **THEN** 系统 SHALL 使用视频标题截断至 10 个字符作为文件名摘要

### Requirement: Analyze Handler 调用方式

`handle_analyze(task, config)` SHALL 作为纯函数，由 `pipeline._run_stages()` 在 analyze 阶段调用。

#### Scenario: 被 pipeline 调用
- **WHEN** pipeline 执行 analyze 阶段
- **THEN** 系统 SHALL 直接调用 `handle_analyze(task, config)`
