{{ config(materialized='table') }}

with base as (
    select
        video_id,
        channel_id,
        title,
        category_id,
        privacy_status,
        published_at,
        loaded_at
    from {{ ref('stg_video_metadata') }}
    where video_id is not null
),

ordered as (
    select
        *,
        row_number() over (
            partition by video_id
            order by loaded_at asc
        ) as rn,
        lag(title) over (
            partition by video_id
            order by loaded_at asc
        ) as prev_title,
        lag(category_id) over (
            partition by video_id
            order by loaded_at asc
        ) as prev_category,
        lag(privacy_status) over (
            partition by video_id
            order by loaded_at asc
        ) as prev_privacy
    from base
),

changes as (
    select
        video_id,
        channel_id,
        title,
        category_id,
        privacy_status,
        published_at,
        loaded_at as effective_from
    from ordered
    where rn = 1
       or coalesce(title, '') <> coalesce(prev_title, '')
       or coalesce(category_id, '') <> coalesce(prev_category, '')
       or coalesce(privacy_status, '') <> coalesce(prev_privacy, '')
),

scd as (
    select
        {{ dbt_utils.generate_surrogate_key(['video_id', 'effective_from']) }} as video_sk,
        video_id,
        channel_id,
        title,
        category_id,
        privacy_status,
        published_at,
        effective_from,
        lead(effective_from) over (
            partition by video_id
            order by effective_from asc
        ) as next_effective_from
    from changes
)

select
    video_sk,
    video_id,
    channel_id,
    title,
    category_id,
    privacy_status,
    published_at,
    effective_from,
    next_effective_from as effective_to,
    case when next_effective_from is null then true else false end as is_current
from scd