"""微信视频号相关单元测试。"""

import pytest


def test_extract_export_id_from_sph_url():
    """验证从 sph 链接中提取 exportId。"""
    from hot_pulse.ingest import _extract_weixin_export_id

    assert _extract_weixin_export_id(
        "https://weixin.qq.com/sph/AoJihY6Lsm"
    ) == "AoJihY6Lsm"

    assert _extract_weixin_export_id(
        "https://weixin.qq.com/sph/abc123"
    ) == "abc123"


def test_fetch_weixin_video_detail_calls_correct_endpoint(monkeypatch):
    """验证 fetch_weixin_video_detail 用正确的 exportId 调 TikHub API。"""
    calls = {}

    class FakeClient:
        def get(self, endpoint, params=None):
            calls["endpoint"] = endpoint
            calls["params"] = params

            class FakeResp:
                def raise_for_status(self): pass
                def json(self):
                    return {
                        "code": 200,
                        "data": {
                            "object_desc": {
                                "media": [{
                                    "url": "https://encrypted.example.com/video",
                                    "url_token": "?token=abc",
                                    "decode_key": "0123456789abcdef0123456789abcdef",
                                }],
                            },
                        },
                    }
            return FakeResp()

    class FakeTikHubClient:
        def __init__(self, config):
            self._client = FakeClient()

    monkeypatch.setattr("hot_pulse.tikhub.TikHubClient", FakeTikHubClient)

    from hot_pulse.tikhub import fetch_weixin_video_detail
    from hot_pulse.config import AppConfig
    result = fetch_weixin_video_detail(None, "TestExportId123")

    assert calls["endpoint"] == "/api/v1/wechat_channels/fetch_video_detail"
    assert calls["params"] == {"exportId": "TestExportId123"}
    assert result["video_id"] == ""
    assert result["encrypted_url"] == "https://encrypted.example.com/video"
    assert result["url_token"] == "?token=abc"
    assert result["decode_key"] == "0123456789abcdef0123456789abcdef"
