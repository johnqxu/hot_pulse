## MODIFIED Requirements

### Requirement: Fetch creator videos from TikHub
The system SHALL call TikHub API endpoint `/api/v1/douyin/app/v3/fetch_user_post_videos` to fetch the latest video list for each configured creator, using their `sec_user_id` as identifier.

#### Scenario: Successfully fetch videos for a creator
- **WHEN** the system queries TikHub API with a valid `sec_user_id`
- **THEN** the system SHALL return a list of video records containing at minimum: video ID, video title, and play URLs from `video.play_addr_h264.url_list`

#### Scenario: TikHub API returns an error
- **WHEN** the TikHub API call fails (network error, rate limit, invalid response)
- **THEN** the system SHALL retry up to 3 times with exponential backoff
- **AND** if all retries fail, the system SHALL log the error and skip this creator, continuing with the next one

#### Scenario: play_addr_h264 node is missing
- **WHEN** a video item does not contain the `video.play_addr_h264` node
- **THEN** the system SHALL fall back to `video.play_addr.url_list`
- **AND** if that is also missing, the system SHALL store an empty JSON array `[]`

### Requirement: Write new video records to Feishu bitable
The system SHALL write each new video as a new record in the Feishu multidimensional table, populating the fields defined in the field mapping.

#### Scenario: Write a single new video record
- **WHEN** a new video is detected for a creator
- **THEN** the system SHALL create a record with the following fields populated:
  - 任务名: video title
  - 优先级: "中"
  - 状态: "新视频"
  - 任务类型: "视频"
  - 平台: "抖音"
  - 博主: creator name
  - 视频链接: JSON string of `play_addr_h264.url_list` array
  - 视频发现时间: current timestamp (milliseconds)
  - 视频ID: video unique ID
  - last_update_time: current timestamp (milliseconds)
- **AND** all other fields (download, transcription, analysis related) SHALL be left empty
