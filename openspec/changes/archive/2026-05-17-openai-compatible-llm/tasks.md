## 1. 配置模型修改

- [x] 1.1 修改 `config.py` 中 `AnalyzeWorkerConfig`：新增 `openai_base_url`（默认 `https://api.deepseek.com/v1`）、`reasoning_effort`（默认 `"high"`）、`extra_body`（默认 `{}`）；修改 `model` 默认值为 `"deepseek-v4-flash"`
- [x] 1.2 修改 `config.py` 中 `SecretConfig`：将 `zhipu_api_key: str = ""` 替换为 `openai_api_key: str = ""`

## 2. analyze_worker 重构

- [x] 2.1 删除 `analyze_worker.py` 中的 `GLM_API_URL` 常量
- [x] 2.2 重命名 `_call_glm_api` 为 `_call_llm_api`，函数内部从 config 读取 `openai_base_url` 和 `secrets.openai_api_key`，URL 拼接为 `f"{openai_base_url}/chat/completions"`
- [x] 2.3 在 `_call_llm_api` 请求体中支持 `reasoning_effort` 字段（非空时添加）和 `extra_body` 展开合并
- [x] 2.4 更新日志消息：所有 "GLM" 字样改为 "LLM"（含 `_call_llm_api`、`_analyze` 中的日志）
- [x] 2.5 更新 `_parse_response` 函数注释：将 "GLM 响应" 改为 "LLM 响应"

## 3. 示例文件更新

- [x] 3.1 更新 `config.yaml.example` 中 `analyze_worker` 段：新增 `openai_base_url`、`reasoning_effort`、`extra_body` 字段及注释说明，model 默认值改为 `deepseek-v4-flash`
- [x] 3.2 更新 `.env.example`：将 `ZHIPU_API_KEY=your_zhipu_api_key_here` 替换为 `OPENAI_API_KEY=your_openai_api_key_here`，附带 DeepSeek 注册链接注释

## 4. 验证

- [x] 4.1 运行 `python -c "from hot_pulse.config import load_config; c = load_config(); print(c.analyze_worker)"` 验证配置加载无报错
- [ ] 4.2 用测试文本端到端跑一次 analyze worker，确认 DeepSeek API 返回正确解析的报告
