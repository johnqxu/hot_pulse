"""Resume video1 from transcribed to knowledge stage."""
import uuid
from pathlib import Path

from hot_pulse.config import load_config
from hot_pulse.task import Task
from hot_pulse.knowledge_worker import handle_knowledge

config = load_config()

# Video 1
task1 = Task(
    task_id=str(uuid.uuid4()),
    task_type="knowledge",
    video_id="BV1tnGm67Eo6_p1",
    title="Harness Engineering 到底是个啥？聊聊大模型技术演进的三个阶段",
    creator="supperz1",
    platform="bilibili",
    source="manual",
    feishu_record_id="manual-resume",
    inputs={"text_file": r"D:\batch\text\BV1tnGm67Eo6_p1.txt"},
)
task1.touch()

result = handle_knowledge(task1, config)
print(f"Video 1 knowledge note: {result.get('obsidian_note', 'FAILED')}")

# Video 2 transcribe still running in background (delta-lagoon)
