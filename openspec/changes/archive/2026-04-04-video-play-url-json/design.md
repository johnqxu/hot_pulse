## Context

当前 monitor 模块从 TikHub API 获取创作者视频列表后，提取 `share_url` 作为视频链接存入飞书。用户需要将 `video.play_addr_h264.url_list` 中的实际播放地址数组以 JSON 格式存储，供后续视频下载使用。

**当前数据流：**
```
TikHub aweme_list[] → share_url → 飞书"视频链接"(type=15 超链接)
```

**目标数据流：**
```
TikHub aweme_list[] → video.play_addr_h264.url_list → JSON字符串 → 飞书"视频链接"(type=1 文本)
```

## Goals / Non-Goals

**Goals:**
- 从 TikHub 响应中提取 `video.play_addr_h264.url_list` 数组
- 将该数组以 JSON 字符串形式写入飞书"视频链接"字段
- 若 `play_addr_h264` 不存在，降级使用 `video.play_addr.url_list`

**Non-Goals:**
- 不修改飞书表格结构（字段类型变更由用户在飞书侧操作）
- 不处理历史记录的迁移

## Decisions

### D1: 降级策略

当 `play_addr_h264` 节点缺失时，按以下优先级降级：
1. `video.play_addr_h264.url_list`
2. `video.play_addr.url_list`
3. 空 JSON 数组 `[]`

### D2: 存储格式

将 `url_list` 数组直接 `json.dumps()` 存入飞书，确保是合法 JSON。

### D3: 飞书字段类型变更

"视频链接"字段当前为 type=15（超链接），存储 JSON 字符串需要改为 type=1（文本）。需提醒用户在飞书侧修改字段类型。

### D4: 修改范围

仅涉及 `tikhub.py`（数据提取）和 `models.py`（字段格式映射），`feishu.py` 和 `monitor.py` 无需修改。

## Risks / Trade-offs

- **[play_addr_h264 节点缺失]** → 部分视频可能没有 H264 播放地址，使用降级策略兜底
- **[URL 时效性]** → `url_list` 中的地址含签名参数，有时效限制，后续下载阶段需及时使用
- **[字段类型不匹配]** → 用户需手动将飞书表格"视频链接"字段从"超链接"改为"文本"
