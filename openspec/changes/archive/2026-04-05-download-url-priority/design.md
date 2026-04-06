## Context

当前 `_download_video()` 遍历 play_urls 列表按原始顺序下载，所有 URL 平等对待。不同 CDN 域名的速度和稳定性差异明显：`*.amemv.com` 通常是抖音官方 CDN，下载快且稳定；`v3-search.douyinvod.com` 等第三方 CDN 速度较慢或易超时。需要在配置中定义域名优先级，下载时优先尝试高优先级地址。

## Goals / Non-Goals

**Goals:**
- 在 DownloadWorkerConfig 中新增 url_priority 配置，支持域名模式到优先级数值的映射
- 下载前根据 url_priority 对 play_urls 排序，优先尝试高优先级 URL

**Non-Goals:**
- 不实现运行时动态优先级调整（优先级在配置中静态定义）
- 不实现基于历史下载速度的自动优先级学习

## Decisions

### D1: 配置格式

使用 `dict[str, int]` 格式，key 为域名模式（支持 `*` 通配符前缀），value 为优先级数值（越大越优先）：

```yaml
download_worker:
  url_priority:
    "*.amemv.com": 10
    "v26-web.douyinvod.com": 5
    "v3-search.douyinvod.com": 0
```

未匹配任何模式的 URL 默认优先级为 0。

### D2: 排序策略

从 URL 中提取域名（`urllib.parse.urlparse`），从最长后缀匹配到配置模式。例如 URL `https://v26-web.douyinvod.com/...` 匹配 `v26-web.douyinvod.com`（精确匹配优先），其次匹配 `*.douyinvod.com`（通配符匹配）。

排序逻辑：
1. 提取 URL 域名
2. 遍历 url_priority 配置，找到匹配的模式（精确匹配优先于通配符）
3. 按优先级降序排序，同优先级保持原始顺序

### D3: 匹配规则

- `*.example.com` 匹配 `sub.example.com`、`a.b.example.com` 等任意子域
- `example.com`（无通配符）仅精确匹配 `example.com` 本身
- 如果 URL 域名匹配多个模式，取优先级最高的

## Risks / Trade-offs

- **[配置维护]** → 新的 CDN 域名出现时需手动更新配置。可接受：域名变化不频繁
- **[通配符过度匹配]** → `*.com` 会匹配所有 .com 域名。缓解：文档说明应使用具体域名模式
