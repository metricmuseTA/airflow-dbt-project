select
  raw:channel_id::string          as channel_id,
  raw:handle::string              as handle,
  raw:channel_title::string       as channel_title,
  raw:uploads_playlist_id::string as uploads_playlist_id,
  raw:pulled_at::timestamp_tz     as pulled_at,
  source_file::string             as source_file,
  current_timestamp()             as loaded_at
from {{ source('raw', 'CHANNEL_REGISTRY_RAW') }}