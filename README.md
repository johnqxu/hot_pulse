# Hot Pulse

抖音创作者内容监控与分析流水线。自动发现新视频，经过多阶段处理后推送分析报告到钉钉群。

## 流水线架构

```
监控发现 → 视频下载 → 音频提取 → 文字转写 → 内容分析 → 钉钉推送
 monitor    download   extract_audio  transcribe   analyze   dingtalk_push
  (定时)    (常驻)      (常驻)        (常驻)       (常驻)     (常驻)
    │         │           │            │            │          │
    └─ZMQ──→ 5551 ──→ 5552 ──→ 5553 ──→ 5554 ──→ 5555 ──→ 5556
```

- **ZMQ PUSH/PULL**: 流水线各阶段间的实时消息传递
- **飞书多维表格**: 唯一持久化状态存储，记录每条视频的处理进度和结果
- **Worker 启动恢复**: 每个 worker 启动时自动从飞书查询未完成任务，继续处理

## 技术栈

- Python 3.10+, 包管理 [uv](https://github.com/astral-sh/uv)
- httpx (同步), pydantic-settings, python-dotenv, loguru, pyyaml
- ZeroMQ (pyzmq): 流水线消息通信
- ffmpeg CLI: 音频提取
- OpenVINO + optimum-intel (Intel GPU) / faster-whisper (CPU 降级): 音频转写
- OpenAI 兼容 LLM API（DeepSeek 等）: 内容分析报告生成
- 钉钉自定义机器人 Webhook: Markdown 报告推送

## 快速开始

### 1. 安装

```bash
# 使用 uv
uv sync

# GPU 加速（Intel GPU）
uv sync --extra gpu
```

### 2. 配置

复制环境变量模板并填写：

```bash
cp .env.example .env
```

编辑 `.env`，填入以下密钥：

| 变量 | 说明 | 必需 |
|------|------|------|
| `TIKHUB_API_KEY` | TikHub API 密钥 | 是 |
| `FEISHU_APP_ID` | 飞书应用 App ID | 是 |
| `FEISHU_APP_SECRET` | 飞书应用 App Secret | 是 |
| `OPENAI_API_KEY` | OpenAI 兼容 API Key（DeepSeek/智谱等） | 是 |
| `DINGTALK_SECRET` | 钉钉机器人加签密钥 | 是 |

编辑 `config.yaml`，配置监控的创作者和各 worker 参数。

### 3. 运行

**一键启动（推荐）：**

```bash
python -m hot_pulse.main
```

启动所有 worker 子进程，等待 30 秒后进入 monitor 定时调度（07:00-24:00，每 59 分钟一次）。按 `Ctrl+C` 优雅关闭。

**独立运行单个 worker：**

```bash
python -m hot_pulse.download_worker
python -m hot_pulse.extract_audio_worker
python -m hot_pulse.transcribe_worker
python -m hot_pulse.analyze_worker
python -m hot_pulse.dingtalk_worker
```

**独立运行 monitor：**

```bash
python -m hot_pulse.monitor
```

可配合系统 cron 或 OpenClaw 定时调度。

## 配置说明

配置分为两部分：

- **`config.yaml`**: 非敏感配置（创作者列表、worker 端点、目录路径等）
- **`.env`**: 敏感信息（API 密钥），不纳入版本控制

### 关键配置项

```yaml
# 监控间隔
schedule:
  interval_minutes: 59

# 创作者列表
creators:
  - name: 口罩哥
    sec_uid: MS4wLjABAAAA...

# TikHub API（主接口失败 3 次后自动降级到备用接口）
tikhub:
  endpoint: /api/v1/douyin/app/v3/fetch_user_post_videos         # 主接口
  fallback_endpoint: /api/v1/douyin/web/fetch_user_post_videos   # 备用接口，设为空禁用

# 各 worker 的 ZMQ 端点和专属配置
download_worker:
  download_dir: "D:\\batch\\video"

transcribe_worker:
  model_dir: "D:\\batch\\whisper-model"
  model_size: "medium"
  device: "gpu"  # gpu(Intel) 或 cpu

analyze_worker:
  model: "deepseek-v4-flash"
  openai_base_url: "https://api.deepseek.com/v1"
  report_dir: "D:\\docs\\财经\\02-市场分析\\视频分析报告"

dingtalk_worker:
  webhook_url: "https://oapi.dingtalk.com/robot/send?access_token=..."
  min_interval: 120  # 钉钉消息流控（秒）
```

## 项目结构

```
src/hot_pulse/
├── main.py                # 主进程编排器，一键启动所有 worker + 定时 monitor
├── monitor.py             # 监控：TikHub → 飞书记录 + ZMQ 推送
├── worker_base.py         # Worker 通用基座（主循环、信号处理、启动恢复）
├── download_worker.py     # 视频下载
├── extract_audio_worker.py # 音频提取（ffmpeg）
├── transcribe_worker.py   # 音频转文字（Whisper）
├── analyze_worker.py      # 内容分析（LLM API → Markdown 报告）
├── dingtalk_worker.py     # 钉钉群消息推送
├── task.py                # Task 数据模型
├── task_manager.py        # 任务状态流转 + 飞书同步
├── feishu.py              # 飞书多维表格客户端
├── tikhub.py              # TikHub API 客户端（主备降级）
├── zmq_client.py          # ZMQ PUSH/PULL 封装
├── config.py              # 配置模型与加载
└── models.py              # 飞书记录数据模型
```

## 状态流转

```
新视频 → 视频下载中 → 视频下载完成 → 音频提取中 → 音频提取完成
  → 文字转写中 → 文字转写完成 → 报告分析中 → 报告分析完成
  → 报告推送中 → 报告推送完成
```

任何阶段失败会转入对应的失败状态（如"视频下载失败"）。Worker 重启后自动恢复未完成的任务。

## 许可证

Private
