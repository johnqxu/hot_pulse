## MODIFIED Requirements

### Requirement: OpenVINO 加速与 CPU 降级
系统 SHALL 在首次加载模型时探测 OpenVINO 后端可用性，成功则使用 OpenVINO GPU 加速（OVWhisperModel），失败则降级到 CPU（FasterWhisperModel）。

OVWhisperModel SHALL 将音频按 30 秒固定窗口切分为不重叠片段，逐段执行 encoder-decoder 推理，拼接完整转写文本。

#### Scenario: OpenVINO GPU 可用 — 短音频（≤30 秒）
- **WHEN** 音频时长 ≤ 30 秒且 OVWhisperModel 已加载
- **THEN** 系统 SHALL 将整段音频送入 encoder 做 1 次推理
- **AND** decoder SHALL 以 max_tokens=448 为上限生成文本

#### Scenario: OpenVINO GPU 可用 — 长音频（>30 秒）
- **WHEN** 音频时长 > 30 秒且 OVWhisperModel 已加载
- **THEN** 系统 SHALL 将音频按 30 秒窗口切分为 N 个片段
- **AND** 每个片段独立执行 encoder-decoder 推理
- **AND** 跳过解码结果为空的片段
- **AND** 非空片段用换行符拼接为完整文本

#### Scenario: 分片边界处理
- **WHEN** 某个 30 秒片段包含静音或纯噪声
- **THEN** decoder SHALL 返回空文本
- **AND** 系统 SHALL 跳过该片段，不输出空行

#### Scenario: OpenVINO 不可用
- **WHEN** 系统首次加载模型且 OpenVINO 后端初始化失败
- **THEN** 系统 SHALL 降级使用 FasterWhisperModel（faster-whisper, device="cpu", compute_type="int8"）
- **AND** 记录警告日志说明 OpenVINO 不可用，已降级到 CPU
