"""patrol_worker 与 pipeline STATUS_TO_STAGE 单元测试。

TDD: patrol-pipeline-migration
"""

import time
from datetime import datetime

import pytest

from hot_pulse.task import Task


# ============================================================================
# STATUS_TO_STAGE 映射测试
# ============================================================================


def test_status_to_stage_includes_all_fail_statuses():
    """验证 STATUS_TO_STAGE 包含所有 fail_status 映射。"""
    from hot_pulse.pipeline import STATUS_TO_STAGE

    fail_cases = {
        "视频下载失败": "download",
        "音频提取失败": "extract_audio",
        "文字转写失败": "transcribe",
        "报告分析失败": "analyze",
        "报告推送失败": "dingtalk_push",
        "知识整理失败": "knowledge",
    }
    for status, expected_stage in fail_cases.items():
        assert STATUS_TO_STAGE.get(status) == expected_stage, (
            f"STATUS_TO_STAGE 缺少 fail_status 映射: {status} → {expected_stage}"
        )


def test_status_to_stage_retains_all_running_statuses():
    """验证扩展后的 STATUS_TO_STAGE 保留所有原有 running/init 状态。"""
    from hot_pulse.pipeline import STATUS_TO_STAGE

    existing_cases = {
        "新视频": "download",
        "视频下载中": "download",
        "音频提取中": "extract_audio",
        "文字转写中": "transcribe",
        "报告分析中": "analyze",
        "报告推送中": "dingtalk_push",
        "知识整理中": "knowledge",
    }
    for status, expected_stage in existing_cases.items():
        assert STATUS_TO_STAGE.get(status) == expected_stage, (
            f"STATUS_TO_STAGE 丢失原有映射: {status} → {expected_stage}"
        )


# ============================================================================
# _is_zombie 测试
# ============================================================================


def make_fields(start_ts_ms: int | None) -> dict:
    """构造飞书 fields dict，包含指定的开始时间戳。"""
    if start_ts_ms is None:
        return {}
    return {"视频下载开始时间": start_ts_ms}


class TestIsZombie:
    """僵尸检测逻辑测试。"""

    def test_elapsed_over_threshold_is_zombie(self, monkeypatch):
        """运行时间超过阈值 → 判定为僵尸。"""
        from hot_pulse.patrol_worker import _is_zombie

        # 模拟 120 分钟前的时间戳
        long_ago = int((datetime.now().timestamp() - 120 * 60) * 1000)
        fields = make_fields(long_ago)
        assert _is_zombie(fields, "视频下载开始时间", 90) is True

    def test_elapsed_under_threshold_not_zombie(self, monkeypatch):
        """运行时间未超阈值 → 不判定为僵尸。"""
        from hot_pulse.patrol_worker import _is_zombie

        # 模拟 30 分钟前的时间戳
        recent = int((datetime.now().timestamp() - 30 * 60) * 1000)
        fields = make_fields(recent)
        assert _is_zombie(fields, "视频下载开始时间", 90) is False

    def test_no_timestamp_is_zombie(self):
        """无时间戳 → 判定为僵尸（异常状态）。"""
        from hot_pulse.patrol_worker import _is_zombie

        assert _is_zombie({}, "视频下载开始时间", 90) is True

    def test_zero_timestamp_is_zombie(self):
        """时间戳为 0 → 判定为僵尸。"""
        from hot_pulse.patrol_worker import _is_zombie

        assert _is_zombie({"视频下载开始时间": 0}, "视频下载开始时间", 90) is True

    def test_non_numeric_timestamp_is_zombie(self):
        """时间戳非数字 → 判定为僵尸。"""
        from hot_pulse.patrol_worker import _is_zombie

        assert _is_zombie(
            {"视频下载开始时间": "not_a_number"}, "视频下载开始时间", 90
        ) is True


# ============================================================================
# _record_to_task 测试
# ============================================================================


def test_record_to_task_constructs_basic_task():
    """_record_to_task 从飞书 fields 构造正确的 Task 对象。"""
    from hot_pulse.feishu import _record_to_task

    fields = {
        "视频ID": [{"text": "v_test_001", "type": "text"}],
        "博主": [{"text": "测试博主", "type": "text"}],
        "任务名": [{"text": "测试视频标题", "type": "text"}],
        "平台": "抖音",
        "来源": "subscription",
        "视频链接": '["http://example.com/video.mp4"]',
    }
    record_id = "rec_test_123"
    task = _record_to_task(fields, record_id, "download")

    assert task is not None
    assert task.video_id == "v_test_001"
    assert task.creator == "测试博主"
    assert task.title == "测试视频标题"
    assert task.platform == "抖音"
    assert task.source == "subscription"
    assert task.feishu_record_id == "rec_test_123"
    assert task.task_type == "download"
    assert task.inputs.get("play_urls") == ["http://example.com/video.mp4"]


def test_record_to_task_default_source():
    """_record_to_task 缺少来源字段时默认 subscription。"""
    from hot_pulse.feishu import _record_to_task

    fields = {
        "视频ID": [{"text": "v_test_002", "type": "text"}],
    }
    task = _record_to_task(fields, "rec_002", "download")
    assert task is not None
    assert task.source == "subscription"


def test_record_to_task_default_platform():
    """_record_to_task 缺少平台字段时默认 '抖音'。"""
    from hot_pulse.feishu import _record_to_task

    fields = {
        "视频ID": [{"text": "v_test_003", "type": "text"}],
    }
    task = _record_to_task(fields, "rec_003", "download")
    assert task is not None
    assert task.platform == "抖音"


def test_record_to_task_no_video_id_returns_none():
    """_record_to_task 无视频ID时返回 None。"""
    from hot_pulse.feishu import _record_to_task

    task = _record_to_task({}, "rec_empty", "download")
    assert task is None


# ============================================================================
# run_patrol 集成测试
# ============================================================================


def test_run_patrol_no_zombie_or_fail_returns_zero(monkeypatch):
    """无僵尸/失败任务时 run_patrol 返回 0。"""
    from hot_pulse.patrol_worker import run_patrol

    # Mock FeishuClient: 所有查询返回空
    class FakeFeishu:
        def close(self):
            pass

        def _ensure_token(self):
            pass

    monkeypatch.setattr(
        "hot_pulse.patrol_worker.FeishuClient",
        lambda c: FakeFeishu(),
    )

    # 让 _query_records_by_status 返回空
    def fake_query(feishu, status):
        return []

    monkeypatch.setattr(
        "hot_pulse.patrol_worker._query_records_by_status", fake_query
    )

    # Mock config
    class FakeSecrets:
        feishu_app_id = "fake_app_id"
        feishu_app_secret = "fake_secret"

    class FakeBitable:
        app_token = "fake_app_token"
        table_id = "fake_table_id"

    class FakeFeishuConfig:
        bitable = FakeBitable()

    class FakePatrolConfig:
        zombie_threshold_minutes = 90

    class FakeConfig:
        secrets = FakeSecrets()
        feishu = FakeFeishuConfig()
        patrol_worker = FakePatrolConfig()

    result = run_patrol(FakeConfig())
    assert result == 0
