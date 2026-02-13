from __future__ import annotations

from googleapiclient.discovery import build

from extract.config import load_config


def get_youtube_client():
    """
    Returns an authenticated YouTube Data API v3 client using an API key.
    Works for public Data API calls (no OAuth).
    """
    cfg = load_config(load_snowflake=False)
    api_key = cfg.youtube.api_key

    # cache_discovery=False avoids cached discovery warnings on some environments
    return build("youtube", "v3", developerKey=api_key, cache_discovery=False)


# Backwards-compatible alias (in case other scripts imported a different name)
get_client = get_youtube_client