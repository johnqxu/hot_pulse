---
name: hot-pulse-ingest
description: >
  将B站或微信视频号视频提交到 Hot Pulse 知识管理管道。
  自动下载、转写、整理为 Obsidian 知识笔记。
trigger:
  - 加入知识库
  - 保存到 Obsidian
  - 记录这个视频
  - 收藏这个视频
  - ingest
  - hot pulse
platforms:
  bilibili:
    patterns:
      - bilibili.com/video/
      - b23.tv/
    type: video
  weixin:
    patterns:
      - weixin.qq.com/sph/
    type: video
---

# Hot Pulse Ingest Skill

将视频内容提交到 Hot Pulse 处理管道，自动完成下载、音频提取、文字转写、知识整理，最终输出到 Obsidian。

## 触发条件

当用户在对话中发送 **B站视频链接** 并表达"加入知识库"、"保存"、"记录"等意图时激活。

## 执行步骤

### 1. 解析用户输入

从用户消息中提取：
- URL：B站视频链接 (bilibili.com/video/BV... 或 b23.tv/...)
- Notes：用户附带的备注或想要重点关注的内容

### 2. 执行命令

```bash
cd D:/workspace/hot_pulse && uv run python -m hot_pulse ingest \
  --type video \
  --platform bilibili \
  --url "<提取的URL>" \
  --notes "<用户的备注>"
```

**注意**: `--title` 参数不传，由 ingest 通过 yt-dlp 自动解析视频标题。

### 3. 反馈用户

成功时获取输出的 JSON `{"task_id":"xxx","status":"submitted"}`，回复用户处理状态。

## 示例对话

**用户**: 把这个视频加入知识库 https://www.bilibili.com/video/BV1xx

**助手**: (执行命令) → 已提交！task_id=xxx，视频将通过下载→转写→知识整理流程，最终出现在 Obsidian 的 inbox 目录。

### 微信视频号

```bash
cd D:/workspace/hot_pulse && uv run python -m hot_pulse ingest \
  --type video \
  --platform weixin \
  --url "<微信视频号 sph 链接>" \
  --notes "<用户的备注>"
```

**注意**: 微信视频号视频通过 TikHub API 下载（自动处理加密解密）。

## 注意事项

- 支持 B站 和 微信视频号，其他平台暂不支持
- 视频处理需要几分钟，处理完成后在 Obsidian `00-Inbox/` 目录查看笔记
- 如需指定重点关注内容，请在消息中附上备注
