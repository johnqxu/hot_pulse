## MODIFIED Requirements

### Requirement: analyze worker handler
系统 SHALL 提供 analyze worker 的 handler 函数，从 Task.inputs 中获取 text_file，读取转写文本，调用 OpenAI 兼容的 LLM API 生成财经内容分析报告。

#### Scenario: 成功生成分析报告
- **WHEN** Task.inputs 包含有效的 text_file 路径
- **THEN** 系统 SHALL 读取转写文本内容
- **AND** 使用配置中指定的 openai_base_url、openai_api_key 和 model 调用 LLM API
- **AND** 将生成的报告保存为 `{report_dir}/{YYYYMMDD}-{creator}-{摘要}.md`
- **AND** 报告文件包含 YAML frontmatter（video_id, platform, creator, title, create_time, analysis_time, tags）
- **AND** 返回 {"report_file": report_file_path}

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

## REMOVED Requirements

### Requirement: GLM API 调用
**Reason**: 替换为通用的 "LLM API 调用" 需求，不再绑定智谱 GLM 专有接口
**Migration**: 将 `openai_base_url` 设置为 `https://open.bigmodel.cn/api/coding/paas/v4`，`model` 设置为 `glm-5.1` 即可恢复智谱调用
