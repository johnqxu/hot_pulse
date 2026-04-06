## 1. 配置模型

- [x] 1.1 config.py 新增 ExtractAudioWorkerConfig（audio_dir 字段）
- [x] 1.2 AppConfig 新增 extract_audio_worker 字段
- [x] 1.3 config.yaml 新增 extract_audio_worker 配置段

## 2. Extract Audio Worker

- [x] 2.1 新增 extract_audio_worker.py：实现 _extract_audio() 和 handle_extract_audio()
- [x] 2.2 新增 extract_audio_worker.py：实现 run_extract_audio_worker()
