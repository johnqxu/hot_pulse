## 1. 依赖与配置

- [x] 1.1 在 pyproject.toml 中添加 `faster-whisper` 依赖，运行 `uv sync` 安装
- [x] 1.2 修改 `config.py`：TranscribeWorkerConfig 增加 `model_size: str = "medium"` 字段
- [x] 1.3 修改 `config.yaml`：transcribe_worker 段增加 `model_size: "medium"`

## 2. 修改 extract_audio_worker

- [x] 2.1 修改 `extract_audio_worker.py`：ffmpeg 输出格式从 MP3 改为 16kHz 单声道 WAV（`-ar 16000 -ac 1`，文件扩展名 `.wav`）

## 3. 新建 transcribe_worker

- [x] 3.1 新建 `transcribe_worker.py`：实现 `_init_model()` 函数，探测 OpenVINO 并降级到 CPU
- [x] 3.2 实现 `_transcribe()` 函数：调用 faster-whisper 转写音频，输出纯文本到 text_dir
- [x] 3.3 实现 `handle_transcribe()` handler 函数：符合 WorkerHandler 签名
- [x] 3.4 实现 `run_transcribe_worker()` 入口函数和 `__main__` CLI 支持
