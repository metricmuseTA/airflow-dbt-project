{{ config(materialized='table') }}

with snaps as (
    select
        video_id,
        channel_id,
        snapshot_at,
        cast(view_count as number)    as view_count,
        cast(like_count as number)    as like_count,
        cast(comment_count as number) as comment_count
    from {{ ref('stg_video_stats_snapshots') }}
    where video_id is not null
      and snapshot_at is not null
),

daily_ranked as (
    select
        video_id,
        channel_id,
        to_date(convert_timezone('UTC', snapshot_at)) as snapshot_date_utc,
        snapshot_at,
        view_count,
        like_count,
        comment_count,
        row_number() over (
            partition by video_id, to_date(convert_timezone('UTC', snapshot_at))
            order by snapshot_at desc
        ) as rn
    from snaps
),

daily as (
    select
        video_id,
        channel_id,
        snapshot_date_utc as date,
        snapshot_at as last_snapshot_at,
        view_count,
        like_count,
        comment_count
    from daily_ranked
    where rn = 1
),

with_keys as (
    select
        d.date,
        v.video_sk,
        c.channel_sk,
        d.video_id,
        d.channel_id,
        d.last_snapshot_at,
        d.view_count,
        d.like_count,
        d.comment_count
    from daily d
    left join {{ ref('dim_video') }} v
      on d.video_id = v.video_id
     and v.is_current = true
    left join {{ ref('dim_channel') }} c
      on d.channel_id = c.channel_id
     and c.is_current = true
)

select * from with_keys