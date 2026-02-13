from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

from dotenv import load_dotenv

# Load environment variables from a local .env file if present.
# (We commit only .env.example, never the real .env.)
load_dotenv()


def _get_env(name: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    Read an environment variable with optional default and required enforcement.
    """
    value = os.getenv(name, default)
    if required and (value is None or str(value).strip() == ""):
        raise ValueError(f"Missing required environment variable: {name}")
    return (value or "").strip()


def _get_first_env(names: list[str], default: str = "", required: bool = False) -> str:
    """
    Return the first non-empty env var from a list of possible names.
    Useful for backwards-compatible renames (e.g. YOUTUBE_API_KEY vs YT_API_KEY).
    """
    for n in names:
        v = os.getenv(n)
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    if required:
        raise ValueError(f"Missing required environment variable. Tried: {', '.join(names)}")
    return default


@dataclass(frozen=True)
class YouTubeConfig:
    """
    YouTube Data API v3 configuration (public data; API key only).
    """
    # Support both names so your .env can be either:
    # - YOUTUBE_API_KEY (recommended)
    # - YT_API_KEY (your current naming)
    api_key: str

    # Optional OAuth fields (not required for Data API-only cohort pulls)
    client_id: str = ""
    client_secret: str = ""

    @staticmethod
    def load() -> "YouTubeConfig":
        api_key = _get_first_env(["YOUTUBE_API_KEY", "YT_API_KEY"], required=True)
        client_id = _get_env("YT_CLIENT_ID", required=False)
        client_secret = _get_env("YT_CLIENT_SECRET", required=False)
        return YouTubeConfig(api_key=api_key, client_id=client_id, client_secret=client_secret)


@dataclass(frozen=True)
class SnowflakeConfig:
    """
    Snowflake connection configuration.
    Only load this when you actually need Snowflake.
    """
    account: str
    user: str
    password: str
    role: str
    warehouse: str
    database: str
    schema: str

    @staticmethod
    def load() -> "SnowflakeConfig":
        return SnowflakeConfig(
            account=_get_env("SNOWFLAKE_ACCOUNT", required=True),
            user=_get_env("SNOWFLAKE_USER", required=True),
            password=_get_env("SNOWFLAKE_PASSWORD", required=False),
            role=_get_env("SNOWFLAKE_ROLE", default=""),
            warehouse=_get_env("SNOWFLAKE_WAREHOUSE", required=True),
            database=_get_env("SNOWFLAKE_DATABASE", required=True),
            schema=_get_env("SNOWFLAKE_SCHEMA", required=True),
        )


@dataclass(frozen=True)
class AppConfig:
    """
    Application-level configuration.
    Note: Snowflake is optional here to avoid breaking YouTube-only scripts.
    """
    env: str
    youtube: YouTubeConfig
    snowflake: Optional[SnowflakeConfig] = None


def load_config(load_snowflake: bool = False) -> AppConfig:
    """
    Primary entrypoint for config loading.

    - load_snowflake=False (default): only requires YouTube env vars.
    - load_snowflake=True: requires Snowflake env vars too.
    """
    env = _get_env("ENV", default="dev")
    youtube = YouTubeConfig.load()
    snowflake = SnowflakeConfig.load() if load_snowflake else None
    return AppConfig(env=env, youtube=youtube, snowflake=snowflake)