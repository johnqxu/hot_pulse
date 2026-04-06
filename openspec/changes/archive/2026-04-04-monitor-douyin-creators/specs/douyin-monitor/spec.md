## ADDED Requirements

### Requirement: Fetch creator videos from TikHub
The system SHALL call TikHub API endpoint `/api/v1/douyin/app/v3/fetch_user_post_videos` to fetch the latest video list for each configured creator, using their `sec_uid` as identifier.

#### Scenario: Successfully fetch videos for a creator
- **WHEN** the system queries TikHub API with a valid `sec_uid`
- **THEN** the system SHALL return a list of video records containing at minimum: video ID, video URL, and video title

#### Scenario: TikHub API returns an error
- **WHEN** the TikHub API call fails (network error, rate limit, invalid response)
- **THEN** the system SHALL retry up to 3 times with exponential backoff
- **AND** if all retries fail, the system SHALL log the error and skip this creator, continuing with the next one

### Requirement: Detect new videos by comparing with existing records
The system SHALL query the Feishu bitable for existing video IDs per creator and compute the difference to identify newly published videos.

#### Scenario: No new videos found
- **WHEN** all videos returned by TikHub already exist in the Feishu bitable for a given creator
- **THEN** the system SHALL skip writing and log "no new videos for {creator_name}"

#### Scenario: New videos found
- **WHEN** TikHub returns videos whose IDs are not present in the Feishu bitable for a given creator
- **THEN** the system SHALL identify those videos as new and prepare them for writing

#### Scenario: First run for a creator with no existing records
- **WHEN** the Feishu bitable has no records for a given creator
- **THEN** all videos returned by TikHub SHALL be treated as new videos

### Requirement: Write new video records to Feishu bitable
The system SHALL write each new video as a new record in the Feishu multidimensional table, populating the fields defined in the field mapping.

#### Scenario: Write a single new video record
- **WHEN** a new video is detected for a creator
- **THEN** the system SHALL create a record with the following fields populated:
  - 任务名: `抖音-{creator_name}-{video_id_prefix}`
  - 优先级: "中"
  - 状态: "待下载"
  - 任务类型: "视频"
  - 任务创建时间: current timestamp
  - 平台: "抖音"
  - 博主: creator name
  - 视频链接: video URL
  - 视频发现时间: current timestamp
  - 视频 ID: video unique ID
  - last_update_time: current timestamp
- **AND** all other fields (download, transcription, analysis related) SHALL be left empty

#### Scenario: Write multiple new videos for a creator
- **WHEN** multiple new videos are detected for a creator
- **THEN** the system SHALL write each video as a separate record to the Feishu bitable

#### Scenario: Feishu API write failure
- **WHEN** writing a record to Feishu bitable fails
- **THEN** the system SHALL log the error and continue with the remaining new videos
- **AND** the system SHALL NOT skip already-written records on next run (idempotency)

### Requirement: Run as independent CLI or importable module
The monitor module SHALL support both standalone execution via `python -m hot_pulse.monitor` and programmatic invocation via `from hot_pulse.monitor import run_monitor`.

#### Scenario: Run as CLI
- **WHEN** user executes `python -m hot_pulse.monitor`
- **THEN** the system SHALL load configuration, iterate all configured creators, detect new videos, and write to Feishu

#### Scenario: Run as imported module
- **WHEN** another module calls `run_monitor()`
- **THEN** the system SHALL perform the same monitoring workflow and return a summary of results

### Requirement: Iterate all configured creators
The system SHALL process each configured creator sequentially, ensuring that a failure for one creator does not prevent processing of subsequent creators.

#### Scenario: One creator fails, others succeed
- **WHEN** processing creator A fails (API error, invalid sec_uid, etc.)
- **THEN** the system SHALL log the error for creator A and continue processing creators B, C, etc.
- **AND** the system SHALL report a summary at the end indicating which creators succeeded and which failed
