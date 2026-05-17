## Context

当前 `tikhub.py` 的 `_do_fetch` 仅调用单一 APP v3 端点，请求参数名使用旧命名（`cursor`/`max_count`）。TikHub 最新 API 文档将参数名改为 `max_cursor`/`count`，且提供了 Web 版作为备用接口。系统需要：先尝试 APP v3 接口（3 次重试），仍失败则降级到 Web 接口。

## Goals / Non-Goals

**Goals:**
- 修正主接口参数名为最新文档规范（`max_cursor`、`count`、`sort_type`）
- 主接口 3 次重试耗尽后自动降级到 Web 备用接口
- 视频列表解析兼容两种接口的响应格式差异
- 配置模型新增 `fallback_endpoint` 字段，可灵活切换或禁用备用

**Non-Goals:**
- 不支持多页翻页（当前系统只需最近视频）
- 不修改 TikHubClient 的公共接口签名
- 不引入异步/并发请求
- 不在 Web 接口上做重试（仅单次调用）

## Decisions

### 1. 主备接口参数映射

```
主接口 (APP v3): /api/v1/douyin/app/v3/fetch_user_post_videos
  参数: sec_user_id, max_cursor (int, 0), count (int, 20), sort_type (int, 0)

备用接口 (Web):   /api/v1/douyin/web/fetch_user_post_videos
  参数: sec_user_id, max_cursor (int, 0), count (int, 20), filter_type (int, 0)
```

两种接口的 `max_cursor`、`count` 参数名一致，`sort_type` vs `filter_type` 不同。设计上 `_do_fetch_primary` 和 `_do_fetch_fallback` 各自构造参数，避免 if/else 分支混淆。

### 2. 流程

```
fetch_user_post_videos(sec_uid)
  │
  ├── _do_fetch_primary(sec_uid)   [retry ×3, 指数退避]
  │     ├─ 成功 → return videos
  │     └─ 3次全失败 → logger.warning("主接口失败，尝试备用接口")
  │
  └── _do_fetch_fallback(sec_uid)  [no retry, 单次]
        ├─ 成功 → return videos
        └─ 失败 → raise (主备均失败)
```

### 3. 配置模型

```python
class TikHubConfig(BaseModel):
    base_url: str = "https://api.tikhub.io"
    endpoint: str = "/api/v1/douyin/app/v3/fetch_user_post_videos"
    fallback_endpoint: str = "/api/v1/douyin/web/fetch_user_post_videos"  # 新增
    max_count: int = 20
```

`fallback_endpoint` 设为空字符串可禁用备用逻辑。

### 4. 为什么不用多遍重试？

Web 接口被 TikHub 官方标记为"可能不稳定"，其本身就不应作为主路径。给 3 次主接口重试 + 1 次备用单次调用，在不无限延长监控时长（4 次 HTTP 调用，约 2 分钟）的前提下提供了合理的容错。

## Risks / Trade-offs

- **[风险] Web 接口响应字段名可能不同**：文档未暴露 `data` 的具体 schema，字段名可能不是 `aweme_list` → **缓解**：视频解析已兼容 `aweme_list` / `videos` / `list` 三种回退
- **[风险] Web 接口被反爬**：可能要求 Cookie → **缓解**：仅作为备用降级，失败时仍抛异常允许上游处理
- **[取舍] Web 接口无重试**：如果主接口和备用接口同时故障，降级失去意义 → 舍：备用接口本来就是紧急备胎，减少额外延迟
