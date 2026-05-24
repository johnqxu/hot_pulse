## Design

### pipeline.py 核心

使用 importlib 动态加载 handler 函数，避免 import-time 绑定导致测试困难。

```python
_SUB_STAGES = (
    ("download", "hot_pulse.download_worker", "handle_download"),
    ...
)

def _run_stages(task, config, stages):
    for stage_name, module, attr in stages:
        handler = importlib.import_module(module).attr
        tm.start(task)
        outputs = handler(task, config)
        tm.finish(task, outputs)
        next_task = tm.build_next(task)
```

### monitor.py 改动

- 删除 `ZmqPublisher` 初始化和 ZMQ 配置检查
- `_process_creator` 去掉 `zmq_pub` 参数，改接 `config`
- 新视频调用 `run_subscription_pipeline(task, config)` 而非 ZMQ push

### ingest.py 改动

- 删除 `_push_and_exit` 函数和 `ZmqPublisher` 导入
- 改为 `run_manual_pipeline(task, config)`
