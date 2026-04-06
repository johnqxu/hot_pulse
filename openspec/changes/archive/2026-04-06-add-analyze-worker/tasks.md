## 1. 依赖与配置

- [x] 1.1 修改 `config.py`：AnalyzeWorkerConfig 增加 `model: str = "glm-5.1"` 和 `prompt: str = ""` 字段；SecretConfig 增加可选字段 `zhipu_api_key: str = ""`
- [x] 1.2 修改 `.env.example`：新增 `ZHIPU_API_KEY=your_zhipu_api_key_here`
- [x] 1.3 修改 `config.yaml`：analyze_worker 段增加 `model: "glm-5.1"` 和 `prompt` 字段（留空则使用内置默认 prompt）

## 2. 新建 analyze_worker

- [x] 2.1 新建 `analyze_worker.py`：实现 `_call_glm_api()` 函数，使用 httpx 同步调用智谱 AI chat completions 接口
- [x] 2.2 实现 `_parse_response()` 函数：从 GLM 响应首行 `<<<SUMMARY>>>...<<<END>>>` 提取 10 字摘要，剩余部分作为报告正文；提取失败时使用视频标题截断兜底
- [x] 2.3 实现 `_build_report()` 函数：组装 YAML frontmatter（从 Task 元数据生成）+ GLM 返回的报告正文，生成完整 Markdown 报告
- [x] 2.4 实现 `_sanitize_filename()` 辅助函数：清理文件名中的非法字符
- [x] 2.4 实现 `handle_analyze()` handler 函数：符合 WorkerHandler 签名，读取转写文本 → 调用 API → 保存报告
- [x] 2.5 实现 `run_analyze_worker()` 入口函数和 `__main__` CLI 支持
