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
    fallback_endpoint: str = "/api/v1/douyin/web/fetch_user_post_videos"
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


class DownloadWorkerConfig(BaseModel):
    download_dir: str = r"D:\batch\video"
    url_priority: dict[str, int] = {}


class ExtractAudioWorkerConfig(BaseModel):
    audio_dir: str = r"D:\batch\audio"


class TranscribeWorkerConfig(BaseModel):
    text_dir: str = r"D:\batch\text"
    model_dir: str = r"D:\batch\whisper-model"
    model_size: str = "medium"
    device: str = "cpu"


class AnalyzeWorkerConfig(BaseModel):
    report_dir: str = r"D:\batch\report"
    model: str = "deepseek-v4-flash"
    prompt: str = ""
    openai_base_url: str = "https://api.deepseek.com/v1"
    reasoning_effort: str = "high"
    extra_body: dict[str, object] = {}


class KnowledgeWorkerConfig(BaseModel):
    obsidian_vault: str = r"D:\docs\Obsidian"
    model: str = ""      # 空则复用 analyze_worker.model
    prompt: str = ""     # 空则用内置默认


class DingTalkWorkerConfig(BaseModel):
    webhook_url: str = ""
    min_interval: int = 120


class PatrolWorkerConfig(BaseModel):
    interval_minutes: int = 60
    zombie_threshold_minutes: int = 90


class SecretConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file_encoding="utf-8",
        extra="ignore",
    )

    tikhub_api_key: str
    feishu_app_id: str
    feishu_app_secret: str
    feishu_bitable_app_token: str = ""
    feishu_bitable_table_id: str = ""
    dingtalk_webhook_url: str = ""
    openai_api_key: str = ""
    dingtalk_secret: str = ""


class AppConfig(BaseModel):
    tikhub: TikHubConfig
    feishu: FeishuConfig
    creators: list[CreatorConfig]
    schedule: ScheduleConfig = ScheduleConfig()
    download_worker: DownloadWorkerConfig = DownloadWorkerConfig()
    extract_audio_worker: ExtractAudioWorkerConfig = ExtractAudioWorkerConfig()
    transcribe_worker: TranscribeWorkerConfig = TranscribeWorkerConfig()
    analyze_worker: AnalyzeWorkerConfig = AnalyzeWorkerConfig()
    knowledge_worker: KnowledgeWorkerConfig = KnowledgeWorkerConfig()
    dingtalk_worker: DingTalkWorkerConfig = DingTalkWorkerConfig()
    patrol_worker: PatrolWorkerConfig = PatrolWorkerConfig()
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

    # 以 config_path 所在目录为基准查找 .env，避免 CWD 不同导致加载失败
    env_path = (config_path.parent / ".env").resolve()
    if env_path.exists():
        # override=True：确保 .env 的值覆盖系统环境变量中的同名变量
        load_dotenv(env_path, override=True)
    else:
        raise FileNotFoundError(f".env 文件不存在: {env_path}")

    try:
        secrets = SecretConfig()  # type: ignore[call-arg]
    except ValidationError as e:
        missing = [err["loc"][0] for err in e.errors()]
        raise ValueError(
            f".env 缺少必要的环境变量: {', '.join(missing)}\n"
            f"请参考 .env.example 创建 .env 文件"
        ) from e

    # 诊断：打印密钥加载状态（脱敏）
    from loguru import logger as _log
    tk = secrets.tikhub_api_key
    fa = secrets.feishu_app_id
    oa = secrets.openai_api_key
    _log.info(
        "配置加载完成: env_path={}, tikhub_key={}, feishu_app_id={}, openai_key={}",
        env_path,
        f"{tk[:8]}..." if tk else "空",
        f"{fa[:8]}..." if fa else "空",
        f"{oa[:8]}..." if oa else "空",
    )

    try:
        config = AppConfig(**raw, secrets=secrets)
    except ValidationError as e:
        raise ValueError(f"配置文件校验失败:\n{e}") from e

    # 用 .env 中的凭证覆盖 YAML 配置
    if secrets.feishu_bitable_app_token:
        config.feishu.bitable.app_token = secrets.feishu_bitable_app_token
    if secrets.feishu_bitable_table_id:
        config.feishu.bitable.table_id = secrets.feishu_bitable_table_id
    if secrets.dingtalk_webhook_url:
        config.dingtalk_worker.webhook_url = secrets.dingtalk_webhook_url

    return config
