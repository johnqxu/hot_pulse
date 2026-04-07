## Context

当前 `OVWhisperModel.transcribe()` 将整个音频文件送入 Whisper encoder 做一次前向推理，再由 decoder 循环生成 token。但 Whisper 架构有两个硬限制：

1. **Encoder positional embedding 上限 1500 帧**（30 秒 @ 100fps），超出部分被截断
2. **Decoder max_tokens=448**，进一步截断输出

对于 5 分钟以上的抖音视频，实际只转写了前 30 秒的内容，导致下游分析报告基于不完整的文本。

`FasterWhisperModel`（CPU 路径）使用 `faster_whisper` 库，内部已实现 VAD 分片，不受此限制。

## Goals / Non-Goals

**Goals:**
- OVWhisperModel 能完整转写任意长度的音频
- 输出格式与 FasterWhisperModel 一致（纯文本，段落间换行）
- 不引入新的外部依赖

**Non-Goals:**
- 不修改 FasterWhisperModel（CPU 路径已正常工作）
- 不修改配置模型或 config.yaml
- 不实现时间戳对齐、说话人识别等高级功能
- 不做 VAD（语音活动检测），使用固定窗口分片即可

## Decisions

### Decision 1: 固定 30 秒窗口分片

将音频按 30 秒（480,000 采样点 @ 16kHz）切分为不重叠的片段，逐段送入 encoder-decoder。

**替代方案：**
- VAD 分片（基于 WebRTCVAD/silero）：更精确但引入新依赖，复杂度高
- 滑动窗口 + 重叠：减少切断单词的风险，但实现复杂，需要去重拼接

**理由：** 固定窗口最简单，Whisper 模型本身就是按 30 秒训练的，对齐模型设计。偶尔切断句子的影响可接受（下游分析不需要逐句精确）。

### Decision 2: 每段独立编码 + 解码

每个 30 秒片段独立执行完整的 feature extraction → encoder → decoder greedy decode 流程。

**理由：** 避免跨段状态传递的复杂度。每段的 token 上下文独立，不会因为前段错误传播影响后续。

### Decision 3: 拼接时去除空段

逐段解码后，跳过空白/纯噪声段（decode 结果为空字符串），非空段用换行拼接。

**理由：** 保持与 FasterWhisperModel 相同的输出格式。

## Risks / Trade-offs

- **[固定窗口可能在词/句中间切断]** → 30 秒窗口对中文语音通常包含 3-5 个完整句子，影响有限。若后续需要更精确的分段，可引入 VAD
- **[逐段推理增加总耗时]** → 每 30 秒一次推理，5 分钟音频需 10 次推理。但每次推理 GPU 耗时约 1-2 秒，总耗时仍在可接受范围
