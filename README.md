# Hot Pulse

抖音创作者内容监控与分析流水线。自动发现新视频，经过多阶段处理后推送分析报告到钉钉群。

## 流水线架构

```
监控发现 → 视频下载 → 音频提取 → 文字转写 → 内容分析 → 钉钉推送 → 知识整理
 monitor    download   extract_audio  transcribe   analyze   dingtalk   knowledge
  (定时)     (串行)     (串行)        (串行)       (串行)     (串行)      (手动)
```

- **单进程串行管道**: 视频发现后按顺序依次执行各阶段，无需消息队列
- **飞书多维表格**: 唯一持久化状态存储，记录每条视频的处理进度和结果
- **启动恢复**: Worker 启动时自动从飞书查询中断任务，从上次失败阶段继续

## 技术栈

- Python 3.10+, 包管理 [uv](https://github.com/astral-sh/uv)
- httpx (同步), pydantic-settings, python-dotenv, loguru, pyyaml
- ffmpeg CLI: 音频提取
- OpenVINO + optimum-intel (Intel GPU) / faster-whisper (CPU 降级): 音频转写
- OpenAI 兼容 LLM API（DeepSeek 等）: 内容分析报告生成
- 钉钉自定义机器人 Webhook: Markdown 报告推送
- yt-dlp: 第三方视频链接解析

## 快速开始

### 1. 安装

```bash
# 使用 uv
uv sync

# GPU 加速（Intel GPU，需额外安装系统运行时）
uv sync --extra gpu
```

#### GPU 加速配置（Intel GPU）

> 仅支持 Intel 集成显卡 / 独立显卡（Iris Xe、Arc 等），不支持 NVIDIA/AMD GPU。

**Arch Linux：**

```bash
# 1. 安装系统 GPU 计算运行时
sudo pacman -S intel-compute-runtime level-zero-loader

# 2. 将用户加入 render 组（获取 /dev/dri/render* 访问权限）
sudo usermod -a -G render $USER

# 3. 重新登录使组生效
```

**验证 OpenVINO 能否识别 GPU：**

```bash
uv run python -c "from openvino.runtime import Core; print('可用设备:', Core().available_devices)"
```

期望输出包含 `GPU`：`可用设备: ['CPU', 'GPU']`。

**如果 GPU 未出现，常见原因：**

| 现象 | 可能原因 | 解决 |
|------|----------|------|
| `GPU` 不在可用设备列表 | 用户不在 `render` 组 | `sudo usermod -a -G render $USER` 并重新登录 |
| `GPU` 不在可用设备列表 | `intel-compute-runtime` 未安装 | `sudo pacman -S intel-compute-runtime` |
| `optimum.intel` 导入失败 | GPU Python 依赖未安装 | `uv sync --extra gpu` |
| 启动日志出现 "GPU 模型加载失败" | 加载出错，自动降级 CPU | 查看 `loguru` 输出的 warning 详情 |

**降级机制：** 代码在 `transcribe_worker.py` 中实现了双重降级——模型初始化失败或推理失败时，会自动回退到 CPU 的 `faster-whisper`，不会报错中断。

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

所有命令通过 `uv run` 执行，无需手动激活 venv。

**一键启动（推荐）：**

```bash
uv run hot-pulse
# 等价于: uv run python -m hot_pulse.main
```

启动主进程，进入 monitor 定时调度（07:00-24:00，间隔由 `schedule.interval_minutes` 决定）。按 `Ctrl+C` 优雅关闭。

**独立运行 monitor（单轮）：**

```bash
uv run hot-pulse-monitor
# 等价于: uv run python -m hot_pulse.monitor
```

可配合系统 cron 或 OpenClaw 定时调度。

**手动提交视频（ingest）：**

```bash
uv run hot-pulse-ingest \
  --type video \
  --platform bilibili \
  --url "https://www.bilibili.com/video/BV1xxx" \
  --notes "可选备注"

# 微信视频号
uv run hot-pulse-ingest \
  --type video \
  --platform weixin \
  --url "https://weixin.qq.com/sph/xxx"
```

**巡检 Worker：**

```bash
uv run hot-pulse-patrol
# 等价于: uv run python -m hot_pulse.patrol_worker
```

> **提示**: 所有 `uv run <脚本名>` 命令都可以用 `uv run python -m hot_pulse.<模块>` 作为等价替代。两者的区别是前者由 `pyproject.toml` 的 `[project.scripts]` 注册，Tab 补全更友好。

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
├── main.py                  # 主进程，定时调度 monitor + 启动恢复
├── monitor.py               # 监控：TikHub → 飞书记录 + 串行管道
├── pipeline.py              # 串行管道编排器，函数式调用各 handler
├── ingest.py                # CLI 手动提交视频到管道处理
├── download_worker.py       # 视频下载
├── extract_audio_worker.py  # 音频提取（ffmpeg）
├── transcribe_worker.py     # 音频转文字（Whisper）
├── analyze_worker.py        # 内容分析（LLM API → Markdown 报告）
├── knowledge_worker.py      # 知识整理（LLM → Obsidian 笔记）
├── dingtalk_worker.py       # 钉钉群消息推送
├── patrol_worker.py         # 巡检：检测僵尸任务并修复
├── task.py                  # Task 数据模型
├── task_manager.py          # 任务状态流转 + 飞书同步
├── feishu.py                # 飞书多维表格客户端
├── tikhub.py                # TikHub API 客户端（主备降级）
├── config.py                # 配置模型与加载
└── models.py                # 飞书记录数据模型

## 状态流转

```
新视频 → 视频下载中 → 视频下载完成 → 音频提取中 → 音频提取完成
  → 文字转写中 → 文字转写完成 → 报告分析中 → 报告分析完成
  → 报告推送中 → 报告推送完成
```

任何阶段失败会转入对应的失败状态（如"视频下载失败"）。Worker 重启后自动恢复未完成的任务。

## 许可证

Private
