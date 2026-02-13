select
  raw:id::string                              as video_id,
  raw:snippet.channelId::string               as channel_id,
  raw:snippet.channelTitle::string            as channel_title,
  raw:snippet.publishedAt::timestamp_tz       as published_at,
  raw:snippet.title::string                   as title,
  raw:snippet.categoryId::string              as category_id,
  raw:snippet.liveBroadcastContent::string    as live_broadcast_content,
  raw:contentDetails.duration::string         as duration_iso8601,
  raw:contentDetails.definition::string       as definition,
  raw:contentDetails.caption::string          as caption,
  raw:status.privacyStatus::string            as privacy_status,
  source_file::string                         as source_file,
  current_timestamp()                         as loaded_at
from {{ source('raw', 'VIDEO_METADATA_RAW') }}