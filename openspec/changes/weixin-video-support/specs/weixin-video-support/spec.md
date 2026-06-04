## Purpose

通过 TikHub API 接入微信视频号内容，支持 sph 分享链接的元信息解析、加密视频下载和解密，纳入标准知识整理管道。

## ADDED Requirements

### Requirement: 微信视频号 CLI 支持

系统 SHALL 支持 `--platform weixin` 作为 ingest CLI 的新选项。

#### Scenario: 参数解析
- **WHEN** 用户传 `--platform weixin --url "https://weixin.qq.com/sph/{exportId}"`
- **THEN** 系统 SHALL 接受该参数组合

### Requirement: TikHub 微信视频号 API 调用

系统 SHALL 通过 TikHubClient 调用 `/api/v1/wechat_channels/fetch_video_detail` 获取视频详情。

#### Scenario: 成功获取视频详情
- **WHEN** TikHub API 返回 200
- **THEN** 系统 SHALL 从响应中提取 title、video_id、uploader、encrypted_url、url_token、decode_key
- **AND** 写入飞书记录并构造 Task(source="manual", platform="weixin")

#### Scenario: API 调用失败
- **WHEN** TikHub API 返回非 200 或网络异常
- **THEN** 系统 SHALL 打印错误信息并非零退出

### Requirement: 微信加密视频下载与解密

系统 SHALL 在 download_worker 中处理 platform="weixin" 的任务，下载加密视频并解密。

#### Scenario: 加密视频下载
- **WHEN** Task.platform="weixin" 且 source="manual"
- **THEN** 系统 SHALL 从 Task.inputs 取 encrypted_url + url_token 拼接完整 URL
- **AND** 通过 httpx 流式下载加密视频文件

#### Scenario: 视频解密
- **WHEN** 加密视频下载完成
- **THEN** 系统 SHALL 使用 Task.inputs.decode_key 对加密视频进行 AES 解密
- **AND** 输出解密后的 mp4 文件到 download_dir

#### Scenario: 下载或解密失败
- **WHEN** 下载或解密过程抛出异常
- **THEN** 系统 SHALL 抛出 RuntimeError 并包含错误详情
