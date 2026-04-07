## 1. 核心改动

- [x] 1.1 修改 `OVWhisperModel.transcribe()`：将音频按 30 秒窗口切分为片段，逐段 encoder-decoder 推理
- [x] 1.2 新增 `_transcribe_chunk()` 辅助方法：对单个 30 秒片段执行 encoder-decoder greedy decode
- [x] 1.3 拼接逻辑：跳过空文本片段，非空段用换行符拼接

## 2. 验证

- [x] 2.1 确认短音频（≤30 秒）行为不变（单次推理，无分片）
- [x] 2.2 确认长音频（>30 秒）输出完整文本，不再被截断
