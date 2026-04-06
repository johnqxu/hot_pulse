## Context

当前流水线：`monitor → download → extract_audio → transcribe → analyze`，analyze 是终端阶段，报告保存到本地 Obsidian 仓库。需要扩展一个新阶段将报告推送到钉钉群。

用户已创建好钉钉自定义机器人，使用加签（HMAC-SHA256）认证方式。报告完整内容不超过 10000 字，钉钉 Markdown 消息上限 20000 字，无需截断。

## Goals / Non-Goals

**Goals:**
- 新增 `dingtalk_push` worker 作为 analyze 之后的流水线终端阶段
- 通过钉钉 Webhook 推送完整 Markdown 报告到群聊
- 实现每条消息间隔 ≥ 2 分钟的流控
- 与现有 worker 架构完全一致（ZMQ 通信、飞书状态同步、启动恢复）

**Non-Goals:**
- 不实现消息模板自定义（使用固定 Markdown 格式）
- 不实现重试机制（由 worker_base 的错误处理兜底）
- 不处理报告截断（报告 < 10000 字，远低于钉钉 20000 字限制）
- 不实现钉钉消息回调或互动按钮

## Decisions

### 1. 流控实现方式：handler 内 time.sleep

**选择**：在 handler 内部记录上次发送时间，若距上次不足 2 分钟则 sleep 补齐。

**替代方案**：使用令牌桶或外部队列限流。

**理由**：流水线本身由 ZMQ 队列缓冲，吞吐量低（日产出视频有限），简单 sleep 即可满足。无需引入额外复杂性。

### 2. 加签认证：标准库 hmac + hashlib

**选择**：使用 Python 标准库 `hmac`、`hashlib`、`base64`、`time`、`urllib.parse` 实现加签。

**理由**：钉钉加签算法简单（timestamp + "\n" + secret → HMAC-SHA256 → base64 → URL encode），无需引入第三方库。

**算法**：
```
timestamp = str(round(time.time() * 1000))
string_to_sign = f"{timestamp}\n{secret}"
hmac_code = hmac.new(secret.encode(), string_to_sign.encode(), hashlib.sha256).digest()
sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
```

### 3. 报告消息格式

**选择**：直接读取报告文件全文作为 Markdown 消息体，title 字段使用视频标题。

**理由**：报告已由 analyze worker 生成标准 Markdown，钉钉支持 Markdown 消息渲染。用户确认报告不超过 10000 字，完整推送无问题。

### 4. handler 输入输出

**输入**：`task.inputs["report_file"]`（由 analyze worker 传递的报告文件路径）
**输出**：`{"push_status": "ok"}`（仅标记推送成功，无文件产出）
**文件操作**：读取报告文件全文

### 5. 流水线位置

analyze 阶段的 `next_type` 从 `None` 改为 `"dingtalk_push"`，dingtalk_push 作为新的终端阶段（`next_type=None`）。

```
analyze (5554 pull → 5555 push)
  → dingtalk_push (5555 pull → 5556 push, 终端无人消费)
```

## Risks / Trade-offs

- **[流控导致延迟]** → 若短时间内多个报告，后续消息需排队等待 2 分钟间隔。可接受：日产出视频有限，延迟无影响。
- **[Webhook URL 泄露]** → Webhook URL 和 Secret 存储在 .env 和 config.yaml 中，与其他 API Key 管理方式一致。
- **[钉钉 Markdown 子集]** → 钉钉 Markdown 不支持表格，报告中的表格会以原文展示。可接受：报告结构已为分析报告格式，核心内容不受影响。
