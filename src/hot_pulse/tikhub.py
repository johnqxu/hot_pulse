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
        self._fallback_endpoint = config.tikhub.fallback_endpoint
        self._max_count = config.tikhub.max_count

        secrets = config.secrets
        if secrets is None:
            raise RuntimeError("config.secrets 为空，请检查 .env 文件是否在 config.yaml 同目录下且包含 TIKHUB_API_KEY")
        self._api_key = secrets.tikhub_api_key
        if not self._api_key:
            raise RuntimeError("TIKHUB_API_KEY 未配置或为空，请检查 .env 文件")

        self._client = httpx.Client(
            base_url=self._base_url,
            headers={"Authorization": f"Bearer {self._api_key}"},
            timeout=30.0,
        )

    def fetch_user_post_videos(self, sec_uid: str) -> list[VideoInfo]:
        """获取指定创作者的最新视频列表。

        优先使用 APP v3 接口（最多 3 次重试），全部失败后降级到 Web 备用接口。
        """
        # 主接口：APP v3，最多 3 次重试
        max_retries = 3
        last_error: Exception | None = None

        for attempt in range(1, max_retries + 1):
            try:
                return self._do_fetch_primary(sec_uid)
            except Exception as e:
                last_error = e
                if attempt < max_retries:
                    wait = 2**attempt
                    logger.warning(
                        f"TikHub 主接口 请求失败 (第{attempt}次), {wait}秒后重试: {e}"
                    )
                    time.sleep(wait)

        logger.error(f"TikHub 主接口 全部失败 (sec_uid={sec_uid}): {last_error}")

        # 备用接口：Web API，不重试
        if not self._fallback_endpoint:
            raise last_error  # type: ignore[misc]

        logger.info("尝试 TikHub 备用接口: endpoint={}", self._fallback_endpoint)
        try:
            return self._do_fetch_fallback(sec_uid)
        except Exception as fb_error:
            logger.error(
                "TikHub 备用接口 也失败 (sec_uid={}): 主接口错误={}, 备用接口错误={}",
                sec_uid, last_error, fb_error,
            )
            raise fb_error

    def _do_fetch_primary(self, sec_uid: str) -> list[VideoInfo]:
        """APP v3 接口：参数含 sort_type。"""
        params = {
            "sec_user_id": sec_uid,
            "count": self._max_count,
            "max_cursor": 0,
            "sort_type": 0,
        }
        return self._request_and_parse(self._endpoint, params)

    def _do_fetch_fallback(self, sec_uid: str) -> list[VideoInfo]:
        """Web 备用接口：参数含 filter_type。"""
        params = {
            "sec_user_id": sec_uid,
            "count": self._max_count,
            "max_cursor": 0,
            "filter_type": 0,
        }
        return self._request_and_parse(self._fallback_endpoint, params)

    def _request_and_parse(self, endpoint: str, params: dict) -> list[VideoInfo]:
        """发送 GET 请求并解析视频列表响应。"""
        response = self._client.get(endpoint, params=params)
        if response.status_code != 200:
            logger.error(
                "TikHub 返回非 200: endpoint={}, status={}, body={}",
                endpoint,
                response.status_code,
                response.text[:1000],
            )
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

        logger.debug(f"TikHub 返回 {len(videos)} 条视频 (endpoint={endpoint})")
        return videos

    def fetch_weixin_video_detail(self, export_id: str) -> dict[str, str]:
        """通过 TikHub API 获取微信视频号视频详情。

        返回: {title, video_id, uploader, encrypted_url, url_token, decode_key}
        """
        resp = self._client.get(
            "/api/v1/wechat_channels/fetch_video_detail",
            params={"exportId": export_id},
        )
        resp.raise_for_status()
        data = resp.json()

        obj_desc = data.get("data", {}).get("object_desc", {})
        title = obj_desc.get("description", "") or obj_desc.get("title", "")
        uploader = data.get("data", {}).get("finder", {}).get("nickname", "")
        video_id = export_id

        media_list = obj_desc.get("media", [])
        encrypted_url = ""
        url_token = ""
        decode_key = ""
        if media_list:
            m = media_list[0]
            encrypted_url = m.get("url", "")
            url_token = m.get("url_token", "")
            decode_key = m.get("decode_key", "")

        if not encrypted_url or not decode_key:
            raise RuntimeError(
                f"TikHub 微信 API 未返回有效视频信息: {data}"
            )

        return {
            "title": title,
            "video_id": video_id,
            "uploader": uploader,
            "encrypted_url": encrypted_url,
            "url_token": url_token,
            "decode_key": decode_key,
        }

    def close(self) -> None:
        self._client.close()
