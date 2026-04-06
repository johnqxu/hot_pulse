from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


class TikHubConfig(BaseModel):
    base_url: str = "https://api.tikhub.io"
    endpoint: str = "/api/v1/douyin/app/v3/fetch_user_post_videos"
    max_count: int = 20


class FeishuBitableConfig(BaseModel):
    app_token: str
    table_id: str


class FeishuConfig(BaseModel):
    bitable: FeishuBitableConfig


class CreatorConfig(BaseModel):
    name: str
    sec_uid: str


class ScheduleConfig(BaseModel):
    interval_minutes: int = 59


class ZeroMQConfig(BaseModel):
    enabled: bool = False
    push_endpoint: str = "tcp://127.0.0.1:5551"


class WorkerConfig(BaseModel):
    """Worker 公共配置基类。"""
    pull_endpoint: str
    push_endpoint: str


class DownloadWorkerConfig(WorkerConfig):
    pull_endpoint: str = "tcp://127.0.0.1:5551"
    push_endpoint: str = "tcp://127.0.0.1:5552"
    download_dir: str = r"D:\batch\video"
    url_priority: dict[str, int] = {}


class ExtractAudioWorkerConfig(WorkerConfig):
    pull_endpoint: str = "tcp://127.0.0.1:5552"
    push_endpoint: str = "tcp://127.0.0.1:5553"
    audio_dir: str = r"D:\batch\audio"


class TranscribeWorkerConfig(WorkerConfig):
    pull_endpoint: str = "tcp://127.0.0.1:5553"
    push_endpoint: str = "tcp://127.0.0.1:5554"
    text_dir: str = r"D:\batch\text"
    model_dir: str = r"D:\batch\whisper-model"
    model_size: str = "medium"
    device: str = "cpu"


class AnalyzeWorkerConfig(WorkerConfig):
    pull_endpoint: str = "tcp://127.0.0.1:5554"
    push_endpoint: str = "tcp://127.0.0.1:5555"
    report_dir: str = r"D:\batch\report"
    model: str = "glm-5.1"
    prompt: str = ""


class DingTalkWorkerConfig(WorkerConfig):
    pull_endpoint: str = "tcp://127.0.0.1:5555"
    push_endpoint: str = "tcp://127.0.0.1:5556"
    webhook_url: str = ""
    min_interval: int = 120


class SecretConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tikhub_api_key: str
    feishu_app_id: str
    feishu_app_secret: str
    zhipu_api_key: str = ""
    dingtalk_secret: str = ""


class AppConfig(BaseModel):
    tikhub: TikHubConfig
    feishu: FeishuConfig
    creators: list[CreatorConfig]
    schedule: ScheduleConfig = ScheduleConfig()
    zeromq: ZeroMQConfig = ZeroMQConfig()
    download_worker: DownloadWorkerConfig = DownloadWorkerConfig()
    extract_audio_worker: ExtractAudioWorkerConfig = ExtractAudioWorkerConfig()
    transcribe_worker: TranscribeWorkerConfig = TranscribeWorkerConfig()
    analyze_worker: AnalyzeWorkerConfig = AnalyzeWorkerConfig()
    dingtalk_worker: DingTalkWorkerConfig = DingTalkWorkerConfig()
    secrets: SecretConfig | None = None


def load_config(config_path: str | Path = "config.yaml") -> AppConfig:
    """加载配置：YAML 非敏感配置 + .env 敏感信息合并。"""
    config_path = Path(config_path)
    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    with open(config_path, encoding="utf-8") as f:
        raw: dict[str, Any] = yaml.safe_load(f)

    if not isinstance(raw, dict):
        raise ValueError(f"配置文件格式错误: {config_path} 应为 YAML 映射")

    load_dotenv()

    try:
        secrets = SecretConfig()  # type: ignore[call-arg]
    except ValidationError as e:
        missing = [err["loc"][0] for err in e.errors()]
        raise ValueError(
            f".env 缺少必要的环境变量: {', '.join(missing)}\n"
            f"请参考 .env.example 创建 .env 文件"
        ) from e

    try:
        config = AppConfig(**raw, secrets=secrets)
    except ValidationError as e:
        raise ValueError(f"配置文件校验失败:\n{e}") from e

    return config
