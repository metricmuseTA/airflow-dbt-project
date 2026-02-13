{{ config(materialized='table') }}

with base as (
    select
        channel_id,
        handle,
        channel_title,
        uploads_playlist_id,
        pulled_at
    from {{ ref('stg_channel_registry') }}
    where channel_id is not null
),

ordered as (
    select
        *,
        row_number() over (
            partition by channel_id
            order by pulled_at asc
        ) as rn,
        lag(handle) over (
            partition by channel_id
            order by pulled_at asc
        ) as prev_handle,
        lag(channel_title) over (
            partition by channel_id
            order by pulled_at asc
        ) as prev_title,
        lag(uploads_playlist_id) over (
            partition by channel_id
            order by pulled_at asc
        ) as prev_uploads
    from base
),

changes as (
    select
        channel_id,
        handle,
        channel_title,
        uploads_playlist_id,
        pulled_at as effective_from
    from ordered
    where rn = 1
       or coalesce(handle, '') <> coalesce(prev_handle, '')
       or coalesce(channel_title, '') <> coalesce(prev_title, '')
       or coalesce(uploads_playlist_id, '') <> coalesce(prev_uploads, '')
),

scd as (
    select
        {{ dbt_utils.generate_surrogate_key(['channel_id', 'effective_from']) }} as channel_sk,
        channel_id,
        handle,
        channel_title,
        uploads_playlist_id,
        effective_from,
        lead(effective_from) over (
            partition by channel_id
            order by effective_from asc
        ) as next_effective_from
    from changes
)

select
    channel_sk,
    channel_id,
    handle,
    channel_title,
    uploads_playlist_id,
    effective_from,
    next_effective_from as effective_to,
    case when next_effective_from is null then true else false end as is_current
from scd