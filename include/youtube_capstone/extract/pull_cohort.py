# extract/pull_cohort.py
from __future__ import annotations

import argparse
import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

# ---- CHANGE THIS ONE LINE if your client factory has a different name ----
# Expected: returns an authenticated googleapiclient.discovery.Resource for YouTube Data API v3
from extract.youtube_client import get_youtube_client  # noqa: F401


REPO_ROOT = Path(__file__).resolve().parents[1]
SEEDS_DIR = REPO_ROOT / "seeds"
RAW_DIR = REPO_ROOT / "data" / "raw"

CHANNEL_REGISTRY_PATH = RAW_DIR / "channel_registry.jsonl"
VIDEO_METADATA_PATH = RAW_DIR / "video_metadata.jsonl"
VIDEO_STATS_SNAPSHOTS_PATH = RAW_DIR / "video_stats_snapshots.jsonl"


@dataclass(frozen=True)
class CohortRow:
    tier: str
    ecosystem: str
    handle: str
    channel_name_hint: str


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)


def read_jsonl_ids(path: Path, key_fn) -> Set[str]:
    """
    Read a JSONL file and return a set of IDs extracted by key_fn(record).
    If file doesn't exist, returns empty set.
    """
    ids: Set[str] = set()
    if not path.exists():
        return ids
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            k = key_fn(rec)
            if k:
                ids.add(k)
    return ids


def append_jsonl(path: Path, records: Iterable[Dict[str, Any]]) -> int:
    count = 0
    with path.open("a", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            count += 1
    return count


def chunked(seq: List[str], n: int) -> Iterable[List[str]]:
    for i in range(0, len(seq), n):
        yield seq[i : i + n]


def load_cohort(csv_path: Path) -> List[CohortRow]:
    rows: List[CohortRow] = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        required = {"tier", "ecosystem", "handle", "channel_name_hint"}
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"creator_cohort.csv missing columns: {sorted(missing)}")

        for r in reader:
            rows.append(
                CohortRow(
                    tier=(r.get("tier") or "").strip(),
                    ecosystem=(r.get("ecosystem") or "").strip(),
                    handle=(r.get("handle") or "").strip(),
                    channel_name_hint=(r.get("channel_name_hint") or "").strip(),
                )
            )
    return rows


# -------------------- YouTube API helpers --------------------

def resolve_channel_by_handle(youtube, handle: str) -> Optional[Dict[str, Any]]:
    """
    Try resolving a channel using channels.list(forHandle=...).
    Handles usually look like '@GarryTan'. We'll try both with and without '@'.
    """
    handle = (handle or "").strip()
    if not handle:
        return None

    candidates = []
    for h in [handle, handle.lstrip("@")]:
        try:
            req = youtube.channels().list(
                part="id,snippet,contentDetails,statistics",
                forHandle=h,
                maxResults=1,
            )
            resp = req.execute()
            items = resp.get("items") or []
            if items:
                return items[0]
        except Exception as e:
            candidates.append(str(e))
            continue
    return None


def resolve_channel_by_search(youtube, query: str) -> Optional[str]:
    """
    Fallback resolution using search.list (type=channel). Returns channelId if found.
    """
    query = (query or "").strip()
    if not query:
        return None
    try:
        req = youtube.search().list(
            part="snippet",
            q=query,
            type="channel",
            maxResults=5,
        )
        resp = req.execute()
        items = resp.get("items") or []
        for it in items:
            cid = (it.get("snippet") or {}).get("channelId")
            if cid:
                return cid
    except Exception:
        return None
    return None


def fetch_channel_by_id(youtube, channel_id: str) -> Optional[Dict[str, Any]]:
    try:
        req = youtube.channels().list(
            part="id,snippet,contentDetails,statistics",
            id=channel_id,
            maxResults=1,
        )
        resp = req.execute()
        items = resp.get("items") or []
        return items[0] if items else None
    except Exception:
        return None


def get_uploads_playlist_id(channel_item: Dict[str, Any]) -> Optional[str]:
    return (
        (channel_item.get("contentDetails") or {})
        .get("relatedPlaylists", {})
        .get("uploads")
    )


def fetch_all_upload_video_ids(
    youtube,
    uploads_playlist_id: str,
    max_videos: Optional[int] = None,
) -> List[str]:
    """
    Pull all videoIds from the channel's uploads playlist.
    """
    video_ids: List[str] = []
    page_token: Optional[str] = None

    while True:
        req = youtube.playlistItems().list(
            part="contentDetails",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=page_token,
        )
        resp = req.execute()
        items = resp.get("items") or []
        for it in items:
            vid = ((it.get("contentDetails") or {}).get("videoId") or "").strip()
            if vid:
                video_ids.append(vid)
                if max_videos and len(video_ids) >= max_videos:
                    return video_ids[:max_videos]

        page_token = resp.get("nextPageToken")
        if not page_token:
            break

    return video_ids


def fetch_videos_metadata(youtube, video_ids: List[str]) -> List[Dict[str, Any]]:
    """
    Fetch videos.list in batches of 50 IDs.
    """
    out: List[Dict[str, Any]] = []
    for batch in chunked(video_ids, 50):
        req = youtube.videos().list(
            part="id,snippet,contentDetails,statistics",
            id=",".join(batch),
            maxResults=50,
        )
        resp = req.execute()
        out.extend(resp.get("items") or [])
    return out


# -------------------- Main run logic --------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Pull cohort channels + videos into JSONL raw files.")
    parser.add_argument("--cohort-csv", default=str(SEEDS_DIR / "creator_cohort.csv"))
    parser.add_argument("--max-videos-per-channel", type=int, default=500)
    parser.add_argument("--snapshot-stats", action="store_true", help="Also write a stats snapshot row per video for today.")
    parser.add_argument("--only-ecosystem", type=str, default="", help="Optional filter, e.g. 'YC' or 'Lenny'.")
    args = parser.parse_args()

    ensure_dirs()

    cohort_csv = Path(args.cohort_csv)
    cohort = load_cohort(cohort_csv)
    if args.only_ecosystem:
        cohort = [r for r in cohort if r.ecosystem.lower() == args.only_ecosystem.lower()]

    # Existing IDs for dedupe
    existing_channel_ids = read_jsonl_ids(CHANNEL_REGISTRY_PATH, lambda r: r.get("channel_id"))
    existing_video_ids = read_jsonl_ids(VIDEO_METADATA_PATH, lambda r: r.get("video_id"))
    existing_snapshot_keys = read_jsonl_ids(
        VIDEO_STATS_SNAPSHOTS_PATH,
        lambda r: f"{r.get('video_id')}|{r.get('snapshot_date')}",
    )

    # Build client
    # If your youtube_client exposes a different factory name, change the import at top.
    youtube = get_youtube_client()

    run_ts = utc_now_iso()
    snapshot_date = run_ts[:10]  # YYYY-MM-DD

    channel_rows_to_write: List[Dict[str, Any]] = []
    video_rows_to_write: List[Dict[str, Any]] = []
    snapshot_rows_to_write: List[Dict[str, Any]] = []

    print(f"Loaded {len(cohort)} cohort rows from {cohort_csv}")
    for row in cohort:
        handle = row.handle.strip()
        hint = row.channel_name_hint.strip()

        # 1) Resolve channel
        channel_item = resolve_channel_by_handle(youtube, handle)
        if not channel_item:
            # fallback search using hint first, else handle
            cid = resolve_channel_by_search(youtube, hint) or resolve_channel_by_search(youtube, handle.lstrip("@"))
            channel_item = fetch_channel_by_id(youtube, cid) if cid else None

        if not channel_item:
            print(f"❌ Could not resolve channel for handle={handle} hint={hint}")
            continue

        channel_id = channel_item.get("id")
        if not channel_id:
            print(f"❌ Resolved channel missing id for handle={handle}")
            continue

        # 2) Write channel registry row (dedup by channel_id)
        if channel_id not in existing_channel_ids:
            snippet = channel_item.get("snippet") or {}
            stats = channel_item.get("statistics") or {}
            uploads_pid = get_uploads_playlist_id(channel_item)

            channel_rows_to_write.append(
                {
                    "channel_id": channel_id,
                    "handle": handle,
                    "channel_name_hint": hint,
                    "tier": row.tier,
                    "ecosystem": row.ecosystem,
                    "title": snippet.get("title"),
                    "description": snippet.get("description"),
                    "published_at": snippet.get("publishedAt"),
                    "country": snippet.get("country"),
                    "uploads_playlist_id": uploads_pid,
                    "statistics": stats,
                    "pulled_at": run_ts,
                    # Keep raw too for traceability
                    "raw": channel_item,
                }
            )
            existing_channel_ids.add(channel_id)

        uploads_playlist_id = get_uploads_playlist_id(channel_item)
        if not uploads_playlist_id:
            print(f"⚠️ Channel {channel_id} has no uploads playlist id; skipping videos.")
            continue

        # 3) Collect video ids from uploads playlist
        video_ids = fetch_all_upload_video_ids(
            youtube,
            uploads_playlist_id=uploads_playlist_id,
            max_videos=args.max_videos_per_channel,
        )
        if not video_ids:
            print(f"⚠️ No videos found for channel: {channel_id}")
            continue

        # 4) Fetch metadata for videos we haven't stored yet
        new_video_ids = [vid for vid in video_ids if vid not in existing_video_ids]
        if new_video_ids:
            video_items = fetch_videos_metadata(youtube, new_video_ids)
            for it in video_items:
                vid = it.get("id")
                if not vid or vid in existing_video_ids:
                    continue
                snip = it.get("snippet") or {}
                video_rows_to_write.append(
                    {
                        "video_id": vid,
                        "channel_id": snip.get("channelId"),
                        "channel_title": snip.get("channelTitle"),
                        "title": snip.get("title"),
                        "published_at": snip.get("publishedAt"),
                        "pulled_at": run_ts,
                        "raw": it,
                    }
                )
                existing_video_ids.add(vid)

        # 5) Optional: write a daily stats snapshot for *all* videos (or at least those present)
        if args.snapshot_stats:
            # Snapshot requires video stats: pull for all ids, but write only new snapshot keys
            all_items = fetch_videos_metadata(youtube, video_ids)  # includes statistics
            for it in all_items:
                vid = it.get("id")
                if not vid:
                    continue
                snap_key = f"{vid}|{snapshot_date}"
                if snap_key in existing_snapshot_keys:
                    continue
                stats = it.get("statistics") or {}
                snapshot_rows_to_write.append(
                    {
                        "video_id": vid,
                        "snapshot_date": snapshot_date,
                        "pulled_at": run_ts,
                        "statistics": stats,
                    }
                )
                existing_snapshot_keys.add(snap_key)

        print(f"✅ {handle} → {channel_id}: videos_seen={len(video_ids)} new_metadata={len(new_video_ids)}")

    # Write outputs
    ch_written = append_jsonl(CHANNEL_REGISTRY_PATH, channel_rows_to_write) if channel_rows_to_write else 0
    vid_written = append_jsonl(VIDEO_METADATA_PATH, video_rows_to_write) if video_rows_to_write else 0
    snap_written = append_jsonl(VIDEO_STATS_SNAPSHOTS_PATH, snapshot_rows_to_write) if snapshot_rows_to_write else 0

    print("\n--- Write Summary ---")
    print(f"channel_registry.jsonl: +{ch_written}")
    print(f"video_metadata.jsonl: +{vid_written}")
    print(f"video_stats_snapshots.jsonl: +{snap_written}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())