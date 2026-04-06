## 1. 核心实现

- [x] 1.1 在 dingtalk_worker.py 中新增 `_strip_frontmatter(text)` 函数，使用正则移除顶部 YAML frontmatter
- [x] 1.2 在 `handle_dingtalk_push` 中读取报告后调用 `_strip_frontmatter` 过滤内容，再传递给 `_send_dingtalk_message`
