## Context

当前 monitor 模块运行流程：TikHub 拉取 → 飞书去重 → 写入飞书表格 → 结束。后续阶段（下载、转写、分析）将以常驻进程方式运行，需要一个通知机制来感知新任务。

## Goals / Non-Goals

**Goals:**
- monitor 发现新视频并写入飞书后，通过 ZMQ PUSH 发送任务消息
- 消息内容为完整的任务信息（JSON 格式）
- ZMQ 连接失败时不阻塞监控主流程，记录错误日志
- ZMQ 端点可配置

**Non-Goals:**
- 不实现 ZMQ 消费端（PULL），后续阶段各自实现
- 不实现消息持久化和重试投递
- 不实现消息确认机制

## Decisions

### D1: ZMQ 模式 — PUSH/PULL

```
monitor (临时进程)                  download (常驻进程)
  PUSH socket ──────────────────────▶  PULL socket
  connect("tcp://127.0.0.1:5551")      bind("tcp://*:5551")
```

- PUSH 端（monitor）用 `connect()`，因为是临时进程
- PULL 端（download）用 `bind()`，因为是常驻进程
- 消息缓存在 PUSH 端内存中（HWM 默认 1000 条）

### D2: 消息格式

任务为中心的 JSON 消息：

```json
{
  "task_id": "uuid4",
  "event": "new_video",
  "stage": "download",
  "video_id": "7624908517552215914",
  "creator": "口罩哥",
  "title": "视频标题",
  "play_urls": ["https://...", "https://..."],
  "feishu_record_id": "recxxxxxx",
  "discovered_at": "2026-04-04T22:54:12"
}
```

### D3: 连接管理

- 每次监控运行时创建 ZMQ Context 和 Socket，运行结束后关闭
- 连接失败时记录错误日志，不阻塞监控主流程
- 不做重连（monitor 是一次性脚本，下次运行会重新连接）

### D4: 项目结构变更

```
src/hot_pulse/
├── zmq_client.py    # 新增：ZMQ PUSH 客户端封装
├── monitor.py       # 修改：飞书写入成功后调用 zmq_client 发送消息
├── config.py        # 修改：新增 ZMQ 配置模型
├── config.yaml      # 修改：新增 zeromq 配置段
```

### D5: 配置格式

```yaml
zeromq:
  enabled: true
  push_endpoint: "tcp://127.0.0.1:5551"
```

## Risks / Trade-offs

- **[下游未启动]** → ZMQ PUSH 消息缓存在发送端内存（HWM 默认 1000），monitor 进程退出后缓存丢失。缓解：飞书表格是持久化真相来源，下游可轮询补偿
- **[消息丢失]** → 纯内存方案，不保证持久化。可接受：飞书表格作为兜底
- **[新增依赖]** → pyzmq (~2MB)，需要 C 扩展编译或预编译 wheel
