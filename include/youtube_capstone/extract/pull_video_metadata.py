from __future__ import annotations

import argparse
from typing import Optional

from extract.io_utils import utc_now_iso, write_jsonl
from extract.youtube_client import get_youtube_client


def resolve_channel_from_handle(youtube, handle: str) -> tuple[str, str, str]:
    handle = handle.strip()
    if handle.startswith("@"):
        handle = handle[1:]

    resp = youtube.channels().list(
        part="id,snippet,contentDetails,statistics",
        forHandle=handle,
        maxResults=1,
    ).execute()

    items = resp.get("items", [])
    if not items:
        raise ValueError(f"No channel found for handle '@{handle}'")

    ch = items[0]
    channel_id = ch["id"]
    title = ch.get("snippet", {}).get("title", "")
    uploads_playlist_id = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    return channel_id, uploads_playlist_id, title


def list_video_ids_from_uploads(youtube, uploads_playlist_id: str, max_videos: Optional[int] = None) -> list[str]:
    video_ids: list[str] = []
    page_token: Optional[str] = None

    while True:
        resp = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=page_token,
        ).execute()

        for it in resp.get("items", []):
            vid = it["contentDetails"]["videoId"]
            video_ids.append(vid)
            if max_videos and len(video_ids) >= max_videos:
                return video_ids[:max_videos]

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return video_ids


def fetch_videos_details(youtube, video_ids: list[str]) -> list[dict]:
    out: list[dict] = []
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i : i + 50]
        resp = youtube.videos().list(
            part="snippet,contentDetails,statistics",
            id=",".join(batch),
            maxResults=50,
        ).execute()
        out.extend(resp.get("items", []))
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--handle", required=True, help='Channel handle, e.g. "@GarryTan"')
    parser.add_argument("--max-videos", type=int, default=25)
    parser.add_argument("--out-dir", default="data/raw")
    args = parser.parse_args()

    youtube = get_youtube_client()
    pulled_at = utc_now_iso()

    channel_id, uploads_playlist_id, channel_title = resolve_channel_from_handle(youtube, args.handle)
    handle = args.handle if args.handle.startswith("@") else f"@{args.handle}"

    print(f"Resolved handle {handle} -> channel_id={channel_id} ({channel_title})")
    print(f"Uploads playlist: {uploads_playlist_id}")

    video_ids = list_video_ids_from_uploads(youtube, uploads_playlist_id, max_videos=args.max_videos)
    print(f"Found {len(video_ids)} video ids.")
    if not video_ids:
        print("No videos found. Exiting.")
        return

    videos = fetch_videos_details(youtube, video_ids)
    print(f"Fetched {len(videos)} video records.")

    # -------------------------
    # WRITE OUTPUTS (JSONL)
    # -------------------------
    write_jsonl(
        f"{args.out_dir}/channel_registry.jsonl",
        [
            {
                "pulled_at": pulled_at,
                "handle": handle,
                "channel_id": channel_id,
                "channel_title": channel_title,
                "uploads_playlist_id": uploads_playlist_id,
            }
        ],
    )

    video_meta_rows = []
    stats_rows = []

    for v in videos:
        vid = v.get("id")
        snippet = v.get("snippet", {}) or {}
        content = v.get("contentDetails", {}) or {}
        stats = v.get("statistics", {}) or {}

        video_meta_rows.append(
            {
                "pulled_at": pulled_at,
                "channel_id": channel_id,
                "video_id": vid,
                "published_at": snippet.get("publishedAt"),
                "title": snippet.get("title"),
                "description": snippet.get("description"),
                "tags": snippet.get("tags", []),
                "category_id": snippet.get("categoryId"),
                "duration": content.get("duration"),
            }
        )

        stats_rows.append(
            {
                "snapshot_at": pulled_at,
                "channel_id": channel_id,
                "video_id": vid,
                "view_count": stats.get("viewCount"),
                "like_count": stats.get("likeCount"),
                "comment_count": stats.get("commentCount"),
            }
        )

    write_jsonl(f"{args.out_dir}/video_metadata.jsonl", video_meta_rows)
    write_jsonl(f"{args.out_dir}/video_stats_snapshots.jsonl", stats_rows)

    first = videos[0]
    print("Sample:")
    print(
        {
            "video_id": first.get("id"),
            "title": first.get("snippet", {}).get("title"),
            "publishedAt": first.get("snippet", {}).get("publishedAt"),
            "views": first.get("statistics", {}).get("viewCount"),
        }
    )
    print(f"WROTE files to: {args.out_dir}")


if __name__ == "__main__":
    main()