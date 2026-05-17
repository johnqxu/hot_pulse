## Context

当前 analyze worker (`analyze_worker.py`) 中 GLM API URL 硬编码为 `https://open.bigmodel.cn/api/coding/paas/v4/chat/completions`，API Key 也通过专属环境变量 `ZHIPU_API_KEY` 获取。切换 LLM 提供商需要改代码。

实际上智谱 GLM、DeepSeek、OpenAI 等主流厂商均采用 OpenAI 兼容的 chat/completions 格式，请求/响应结构完全一致。只需要将 URL、Key、Model 三项参数化即可实现"切换改配置"。

目标默认提供商：**DeepSeek V4 Flash**（284B/13B 激活，¥1/¥2 百万 tokens，1M 上下文，性价比较高）。DeepSeek V4 还提供了 `thinking` 开关和 `reasoning_effort` 参数来控制推理深度，需通过通用接口承载。

## Goals / Non-Goals

**Goals:**
- API URL 从配置读取，不再硬编码
- API Key 从专属 `ZHIPU_API_KEY` 改为通用 `OPENAI_API_KEY`
- `model` 默认值改为 `deepseek-v4-flash`
- 支持通过 `extra_body` 传递厂商专属参数（如 DeepSeek 的 `thinking: {type: "enabled"}`）
- 支持 `reasoning_effort` 参数控制推理深度（OpenAI o 系列和 DeepSeek 均支持）
- 切换回智谱或其他 OpenAI 兼容厂商无需改代码

**Non-Goals:**
- 不引入 OpenAI 官方 SDK（保持轻量，httpx 直发请求）
- 不支持流式输出（分析报告的 use case 不需要）
- 不支持多模型并发/fallback 策略（保持简单，一个模型一个配置）
- 不修改 Prompt 内容（现有 Prompt 保持不变，先跑起来看效果）

## Decisions

### 1. 配置模型设计

`AnalyzeWorkerConfig` 新增三个字段：

```python
class AnalyzeWorkerConfig(WorkerConfig):
    pull_endpoint: str = "tcp://127.0.0.1:5554"
    push_endpoint: str = "tcp://127.0.0.1:5555"
    report_dir: str = r"D:\batch\report"
    model: str = "deepseek-v4-flash"          # 改默认值
    prompt: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"  # 新增
    reasoning_effort: str = "high"            # 新增
    extra_body: dict = {}                     # 新增
```

`SecretConfig` 变更：

```python
class SecretConfig(BaseSettings):
    # ... 其他字段不变 ...
    openai_api_key: str = ""  # 替代原来的 zhipu_api_key
```

**为什么不在 SecretConfig 中保留 `zhipu_api_key` 向后兼容？** 因为这不是库是对内项目，运维者可手动更新 `.env`。保持配置模型干净，避免遗留字段。

### 2. `openai_base_url` 的设计

该字段存的是 LLM 服务的基础路径（不含 `/chat/completions`），完整端点由代码拼接：

```
f"{openai_base_url}/chat/completions"
```

这样符合 OpenAI 标准，DeepSeek (`https://api.deepseek.com/v1`) 和智谱 (`https://open.bigmodel.cn/api/coding/paas/v4`) 都遵循此约定，仅值不同。

### 3. `extra_body` 的设计

`extra_body` 是一个自由 dict，代码直接 merge 进请求体。用于承载厂商专属参数：

```yaml
# DeepSeek 开启思考模式
analyze_worker:
  extra_body:
    thinking:
      type: "enabled"

# 智谱 GLM（不需要专属参数）
analyze_worker:
  extra_body: {}

# OpenAI o 系列
analyze_worker:
  extra_body: {}
```

`reasoning_effort` 则单独放在请求体顶层（因为它是 OpenAI 标准参数，o 系列和 DeepSeek 都支持）：

```python
payload = {
    "model": model,
    "messages": [...],
    "temperature": 0.7,
    "reasoning_effort": reasoning_effort,  # 顶层标准字段
    **extra_body,                           # 厂商专属展开
}
```

### 4. 方法重命名

| 旧名 | 新名 | 说明 |
|------|------|------|
| `_call_glm_api()` | `_call_llm_api()` | 不再与智谱绑定 |
| `GLM_API_URL` | 删除 | 从 config 读取 |
| `_parse_response()` 中注释 "GLM 响应" | 改为 "LLM 响应" | 注释措辞 |

日志中的 "GLM" 字样同步修改为 "LLM"。

### 5. 兼容性处理

`_call_llm_api` 保持与旧的 `_call_glm_api` 相同的函数签名 `(text: str, config: AppConfig) -> str`，调用方 `_analyze()` 无需修改。

错误信息中不再出现 "GLM" 字样，改为通用的 "LLM API"。

## Risks / Trade-offs

- **[风险] DeepSeek 思考模式下输出格式可能不同**：思考模式下会在响应中插入 `<think>...</think>` 标签，可能影响 `_parse_response` 的首行解析。→ **缓解**：先用 Think High 模式测试，如果摘要行被 `<think>` 包裹导致解析失败，就在 `_parse_response` 中增加 `<think>` 剥离逻辑。

- **[风险] token 消耗差异**：DeepSeek 的 tokenizer 与智谱不同，相同文本 token 量不同，可能导致成本预估不准。→ **缓解**：先跑几条视频看实际消耗，必要时调整超时（当前 300 秒已经够宽松）。

- **[取舍] 不支持多 provider 热切换**：一次只能配一个 provider。如果未来需要主备切换，需重启 worker。→ 当前场景单用户单 pipeline，不需要此复杂度。真需要时加 provider 字段 + 映射表。

## Migration Plan

1. 更新 `config.py` 中的配置模型
2. 修改 `analyze_worker.py` 的 `_call_glm_api` → `_call_llm_api`
3. 更新 `config.yaml.example` 和 `.env.example`
4. 运维者手动更新 `.env`：改 `ZHIPU_API_KEY` 为 `OPENAI_API_KEY`，填入 DeepSeek API Key
5. 运维者更新 `config.yaml`：确认 `openai_base_url` 和 `model` 为新默认值
6. 重启 analyze worker 验证

**回滚**：将 `openai_base_url` 改回 `https://open.bigmodel.cn/api/coding/paas/v4`，`model` 改回 `glm-5.1`，Key 名称手动改回即可。

## Open Questions

- 无。所有决策已在上述章节中明确。
