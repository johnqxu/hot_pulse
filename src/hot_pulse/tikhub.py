from __future__ import annotations

import time

import httpx
from loguru import logger

from hot_pulse.config import AppConfig, TikHubConfig
from hot_pulse.models import VideoInfo


class TikHubClient:
    """TikHub API 客户端，用于获取抖音创作者视频列表。"""

    def __init__(self, config: AppConfig) -> None:
        self._base_url = config.tikhub.base_url
        self._endpoint = config.tikhub.endpoint
        self._max_count = config.tikhub.max_count
        self._api_key = config.secrets.tikhub_api_key
        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )

    def fetch_user_post_videos(self, sec_uid: str) -> list[VideoInfo]:
        """获取指定创作者的最新视频列表，带重试机制（最多3次，指数退避）。"""
        max_retries = 3
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                return self._do_fetch(sec_uid)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2**attempt
                    logger.warning(
                        f"TikHub 请求失败 (第{attempt}次), {wait}秒后重试: {e}"
                    )
                    time.sleep(wait)

        logger.error(f"TikHub 请求全部失败 (sec_uid={sec_uid}): {last_error}")
        raise last_error  # type: ignore[misc]

    def _do_fetch(self, sec_uid: str) -> list[VideoInfo]:
        params = {
            "sec_user_id": sec_uid,
            "max_count": self._max_count,
            "cursor": 0,
        }
        response = self._client.get(self._endpoint, params=params)
        response.raise_for_status()
        data = response.json()

        videos: list[VideoInfo] = []
        items = data.get("data", {}).get("aweme_list", [])
        if not items:
            items = data.get("data", {}).get("videos", [])
        if not items:
            items = data.get("data", {}).get("list", [])

        for item in items:
            try:
                video_id = str(
                    item.get("aweme_id")
                    or item.get("id")
                    or item.get("vid", "")
                )
                title = (
                    item.get("item_title")
                    or item.get("desc")
                    or item.get("title")
                    or ""
                )
                url = item.get("share_url", "")

                # 提取视频播放地址
                video_node = item.get("video", {})
                play_urls: list[str] = []
                h264 = video_node.get("play_addr_h264", {})
                if h264 and h264.get("url_list"):
                    play_urls = h264["url_list"]
                elif video_node.get("play_addr", {}).get("url_list"):
                    play_urls = video_node["play_addr"]["url_list"]

                if not video_id:
                    logger.warning(f"跳过无视频ID的记录: {item}")
                    continue

                videos.append(VideoInfo(video_id=video_id, title=title, url=url, play_urls=play_urls))
            except Exception as e:
                logger.warning(f"解析视频记录失败，跳过: {e}")
                continue

        # TikHub API 可能忽略 max_count 参数，在客户端侧截断
        if len(videos) > self._max_count:
            videos = videos[: self._max_count]

        logger.debug(f"TikHub 返回 {len(videos)} 条视频 (sec_uid={sec_uid[:16]}...)")
        return videos

    def close(self) -> None:
        self._client.close()
