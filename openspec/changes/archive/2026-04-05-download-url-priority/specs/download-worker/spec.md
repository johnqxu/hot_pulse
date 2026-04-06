## MODIFIED Requirements

### Requirement: 视频下载处理
系统 SHALL 提供 download worker 的 handler，从 Task.inputs 中获取 play_urls，按域名优先级排序后依次尝试下载视频。

#### Scenario: 按优先级排序下载
- **WHEN** play_urls 包含多个不同域名的 URL
- **THEN** 系统 SHALL 根据 config 中 url_priority 配置对 URL 按优先级降序排序
- **AND** 按排序后的顺序依次尝试下载

#### Scenario: URL 无匹配优先级配置
- **WHEN** 某 URL 的域名不匹配 url_priority 中的任何模式
- **THEN** 系统 SHALL 将该 URL 的优先级视为 0

#### Scenario: 优先级相同的 URL
- **WHEN** 多个 URL 的域名匹配到相同的优先级数值
- **THEN** 系统 SHALL 保持这些 URL 的原始顺序

#### Scenario: 所有地址均失败
- **WHEN** 排序后的所有 URL 均下载失败
- **THEN** 系统 SHALL 抛出 RuntimeError
