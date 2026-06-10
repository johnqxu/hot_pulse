"""pipeline.py 单元测试 — 串行管道编排器。"""

import pytest

from hot_pulse.pipeline import run_manual_pipeline, run_subscription_pipeline


def test_run_subscription_pipeline_exists():
    """验证 subscription pipeline 函数存在且可调用。"""
    assert callable(run_subscription_pipeline)


# 测试 2: subscription pipeline 按顺序调用 handler


def test_subscription_pipeline_calls_handlers_in_order(monkeypatch):
    """验证 subscription 管道按 download → extract → transcribe → analyze → dingtalk 顺序调用。"""
    call_order = []

    def fake_download(task, config):
        call_order.append("download")
        return {"video_file": "/tmp/test.mp4"}

    def fake_extract(task, config):
        call_order.append("extract")
        return {"audio_file": "/tmp/test.wav"}

    def fake_transcribe(task, config):
        call_order.append("transcribe")
        return {"text_file": "/tmp/test.txt"}

    def fake_analyze(task, config):
        call_order.append("analyze")
        return {"report_file": "/tmp/test.md"}

    def fake_dingtalk(task, config):
        call_order.append("dingtalk")
        return {}

    # Mock 到原始 worker 模块（pipeline.py 的 _HANDLERS 是 import-time tuple）
    monkeypatch.setattr(
        "hot_pulse.download_worker.handle_download", fake_download
    )
    monkeypatch.setattr(
        "hot_pulse.extract_audio_worker.handle_extract_audio", fake_extract
    )
    monkeypatch.setattr(
        "hot_pulse.transcribe_worker.handle_transcribe", fake_transcribe
    )
    monkeypatch.setattr(
        "hot_pulse.analyze_worker.handle_analyze", fake_analyze
    )
    monkeypatch.setattr(
        "hot_pulse.dingtalk_worker.handle_dingtalk_push", fake_dingtalk
    )

    # Mock FeishuClient 和 TaskManager
    class FakeFeishu:
        def close(self): pass
        def update_record(self, *a, **kw): pass
        def create_records(self, *a, **kw): return []

    monkeypatch.setattr("hot_pulse.pipeline.FeishuClient", lambda c: FakeFeishu())

    from hot_pulse.task import Task

    task = Task(
        task_id="t1",
        task_type="download",
        video_id="v1",
        creator="c",
        title="t",
        inputs={"play_urls": ["http://x.mp4"]},
    )

    run_subscription_pipeline(task, None)

    assert call_order == [
        "download", "extract", "transcribe", "analyze", "dingtalk"
    ]


def test_subscription_pipeline_stops_on_failure(monkeypatch):
    """验证管道中某个阶段失败时，后续阶段不再执行。"""
    call_order = []

    def fake_download(task, config):
        call_order.append("download")
        return {"video_file": "/tmp/test.mp4"}

    def fake_extract(task, config):
        call_order.append("extract")
        raise RuntimeError("ffmpeg 提取失败")

    def fake_transcribe(task, config):
        call_order.append("transcribe")
        return {"text_file": "/tmp/test.txt"}

    monkeypatch.setattr(
        "hot_pulse.download_worker.handle_download", fake_download
    )
    monkeypatch.setattr(
        "hot_pulse.extract_audio_worker.handle_extract_audio", fake_extract
    )
    monkeypatch.setattr(
        "hot_pulse.transcribe_worker.handle_transcribe", fake_transcribe
    )

    class FakeFeishu:
        def close(self): pass
        def update_record(self, *a, **kw): pass
        def create_records(self, *a, **kw): return []

    monkeypatch.setattr("hot_pulse.pipeline.FeishuClient", lambda c: FakeFeishu())

    from hot_pulse.task import Task

    task = Task(
        task_id="t2",
        task_type="download",
        video_id="v2",
        creator="c",
        title="t",
        inputs={"play_urls": ["http://x.mp4"]},
    )

    with pytest.raises(RuntimeError, match="ffmpeg"):
        run_subscription_pipeline(task, None)

    # download 和 extract 执行了, 但 transcribe 不应该执行
    assert call_order == ["download", "extract"]


def test_run_manual_pipeline_calls_knowledge_handler(monkeypatch):
    """验证 manual 管道: download → extract → transcribe → knowledge。"""
    call_order = []

    def fake_download(task, config):
        call_order.append("download")
        return {"video_file": "/tmp/test.mp4"}

    def fake_extract(task, config):
        call_order.append("extract")
        return {"audio_file": "/tmp/test.wav"}

    def fake_transcribe(task, config):
        call_order.append("transcribe")
        return {"text_file": "/tmp/test.txt"}

    def fake_knowledge(task, config):
        call_order.append("knowledge")
        return {"obsidian_note": "/tmp/test.md"}

    monkeypatch.setattr(
        "hot_pulse.download_worker.handle_download", fake_download
    )
    monkeypatch.setattr(
        "hot_pulse.extract_audio_worker.handle_extract_audio", fake_extract
    )
    monkeypatch.setattr(
        "hot_pulse.transcribe_worker.handle_transcribe", fake_transcribe
    )
    monkeypatch.setattr(
        "hot_pulse.knowledge_worker.handle_knowledge", fake_knowledge
    )

    class FakeFeishu:
        def close(self): pass
        def update_record(self, *a, **kw): pass
        def create_records(self, *a, **kw): return []

    monkeypatch.setattr("hot_pulse.pipeline.FeishuClient", lambda c: FakeFeishu())

    from hot_pulse.task import Task

    task = Task(
        task_id="t3",
        task_type="download",
        video_id="v3",
        creator="c",
        title="t",
        source="manual",
        inputs={"play_urls": ["http://x.mp4"]},
    )

    run_manual_pipeline(task, None)

    assert call_order == [
        "download", "extract", "transcribe", "knowledge"
    ]


def test_pipeline_can_start_from_middle(monkeypatch):
    """验证管道从中间 stage 恢复: 跳过前面的 stage。"""
    call_order = []

    def fake_extract(task, config):
        call_order.append("extract")
        return {"audio_file": "/tmp/test.wav"}

    def fake_transcribe(task, config):
        call_order.append("transcribe")
        return {"text_file": "/tmp/test.txt"}

    def fake_analyze(task, config):
        call_order.append("analyze")
        return {"report_file": "/tmp/test.md"}

    def fake_dingtalk(task, config):
        call_order.append("dingtalk")
        return {}

    monkeypatch.setattr(
        "hot_pulse.extract_audio_worker.handle_extract_audio", fake_extract
    )
    monkeypatch.setattr(
        "hot_pulse.transcribe_worker.handle_transcribe", fake_transcribe
    )
    monkeypatch.setattr(
        "hot_pulse.analyze_worker.handle_analyze", fake_analyze
    )
    monkeypatch.setattr(
        "hot_pulse.dingtalk_worker.handle_dingtalk_push", fake_dingtalk
    )

    class FakeFeishu:
        def close(self): pass
        def update_record(self, *a, **kw): pass
        def create_records(self, *a, **kw): return []

    monkeypatch.setattr("hot_pulse.pipeline.FeishuClient", lambda c: FakeFeishu())

    from hot_pulse.task import Task

    task = Task(
        task_id="t4",
        task_type="extract_audio",
        video_id="v4", creator="c", title="t",
        source="subscription",
        feishu_record_id="rec123",
        inputs={"video_file": "/tmp/existing.mp4"},
    )

    run_subscription_pipeline(task, None, start_stage="extract_audio")

    # download 不应出现，直接从 extract 开始
    assert "download" not in call_order
    assert call_order[:2] == ["extract", "transcribe"]


def test_status_to_stage_mapping():
    """验证飞书状态到 pipeline stage 的映射正确。"""
    from hot_pulse.pipeline import STATUS_TO_STAGE

    assert STATUS_TO_STAGE["新视频"] == "download"
    assert STATUS_TO_STAGE["视频下载中"] == "download"
    assert STATUS_TO_STAGE["音频提取中"] == "extract_audio"
    assert STATUS_TO_STAGE["文字转写中"] == "transcribe"
    assert STATUS_TO_STAGE["报告分析中"] == "analyze"
    assert STATUS_TO_STAGE["报告推送中"] == "dingtalk_push"
    assert STATUS_TO_STAGE["知识整理中"] == "knowledge"
