## Context

微信视频号 (`channels.weixin.qq.com`) 是微信内的短视频平台。yt-dlp 不支持该平台的视频解析。TikHub 提供了 `/api/v1/wechat_channels/fetch_video_detail` API 端点，可获取视频详情（含加密视频 URL 和解密密钥）。

## Goals / Non-Goals

**Goals:**
- `--platform weixin` 作为 ingest CLI 的新选项
- 通过 TikHub API 获取微信视频号元信息（title, video_id, uploader）
- download_worker 支持微信加密视频的下载和解密
- 后续管道（extract → transcribe → knowledge）完全复用

**Non-Goals:**
- 不自行实现微信视频号页面爬取（依赖 TikHub API）
- 解密工具封装在 download_worker 内部，不暴露独立 CLI

## Decisions

### 1. 整体流程

```
用户: --platform weixin --url "https://weixin.qq.com/sph/AoJihY6Lsm"

ingest.py:
  1. 从 sph URL 提取视频号 ID
  2. 调 TikHub API (/api/v1/wechat_channels/fetch_video_detail)
  3. 获取: title, uploader, video_id, encrypted_url, url_token, decode_key
  4. 写飞书记录 + 构造 Task(source="manual")

download_worker.py:
  场景: source="manual" AND platform="weixin"
  1. 从 Task.inputs 取 encrypted_url, url_token, decode_key
  2. 拼接完整 URL: encrypted_url + url_token
  3. httpx 流式下载加密视频
  4. 用 decode_key 解密 → 写入 mp4 文件
  5. 返回 video_file
```

### 2. TikHubClient 新增方法

```python
def fetch_weixin_video_detail(self, export_id: str) -> dict:
    """获取微信视频号视频详情。
    返回: {title, video_id, uploader, encrypted_url, url_token, decode_key}
    """
    resp = self._client.get(
        "/api/v1/wechat_channels/fetch_video_detail",
        params={"exportId": export_id},
    )
    ...
```

### 3. 视频 ID 提取

微信视频号分享链接格式: `https://weixin.qq.com/sph/{exportId}`。

在 ingest.py 中新增 `_resolve_weixin_url(url)` 函数：
- 正则提取 `sph/` 后的 exportId
- 调 `TikHubClient.fetch_weixin_video_detail(exportId)`
- 从 TikHub 通用响应结构（`$.data.object_desc`）中按实际 JSON 路径提取字段，不假设根级字段名
- 返回 `(title, video_id, uploader, encrypted_url, url_token, decode_key)`

### 4. 解密方案

视频 AES 解密使用 `decode_key` 参数。下载加密视频后，用 Python 的 `pycryptodome`（`Crypto.Cipher.AES`）在内存中解密，写入输出文件。

**注意：以下 AES 模式（CBC + key 作为 iv）为初始假设，实现时需用真实 API 响应进行验证。** 如解密失败，参考官方解密工具（`WeChat-Channels-Video-File-Decryption`）调整模式和 iv。

```python
from Crypto.Cipher import AES

def _decrypt_video(encrypted_data: bytes, decode_key: str) -> bytes:
    """用 decode_key 解密微信视频号加密视频。
    注意：AES 模式和 IV 需要在真实数据上验证。
    """
    key = bytes.fromhex(decode_key)
    cipher = AES.new(key, AES.MODE_CBC, iv=key)
    return cipher.decrypt(encrypted_data)
```

### 5. download_worker 路由

```python
# handle_download 中
if task.source == "manual":
    if task.platform == "weixin":
        video_file = _download_via_tikhub_weixin(task, config)
    else:
        video_file = _download_via_ytdlp(task.video_id, source_url, download_dir)
```

## Risks / Trade-offs

- **[风险] TikHub 微信 API 可用性**: 需确认用户 TikHub 账号有该端点的访问权限
- **[风险] 解密逻辑准确度**: 微信加密算法可能变化 → **缓解**: 在 `_download_via_tikhub_weixin` 中做完整异常处理
- **[取舍] 新增 pycryptodome 依赖**: 需要 `pip install pycryptodome` → 是 Python 标准密码库，可靠性高
