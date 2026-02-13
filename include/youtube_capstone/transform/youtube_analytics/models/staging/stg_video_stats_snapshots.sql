select
  raw:video_id::string                 as video_id,
  raw:channel_id::string               as channel_id,
  raw:snapshot_at::timestamp_tz        as snapshot_at,
  raw:view_count::number               as view_count,
  raw:like_count::number               as like_count,
  raw:comment_count::number            as comment_count,
  raw:favorite_count::number           as favorite_count,
  source_file::string                  as source_file,
  current_timestamp()                  as loaded_at
from {{ source('raw', 'VIDEO_STATS_SNAPSHOTS_RAW') }}