## Why

analyze worker 生成的报告包含 Obsidian YAML frontmatter（`---` 包裹的元数据块），用于本地笔记管理。推送钉钉群时这部分信息对读者无意义，影响阅读体验，需要过滤掉。

## What Changes

- dingtalk_worker 在发送报告前，检测并移除 Markdown 文件顶部的 YAML frontmatter（`---` 开头和结尾的块）
- 仅影响钉钉推送内容，不影响本地保存的报告文件

## Capabilities

### New Capabilities

（无新增能力）

### Modified Capabilities
- `dingtalk-push-worker`: 推送前需对报告内容进行 frontmatter 过滤处理

## Impact

- 修改文件：`src/hot_pulse/dingtalk_worker.py`（handler 中增加过滤逻辑）
