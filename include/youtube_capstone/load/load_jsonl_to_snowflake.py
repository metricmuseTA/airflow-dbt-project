import json
import os
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv

# Load .env exactly like your successful one-liner (run from repo root)
load_dotenv(override=True)

REPO_ROOT = Path.cwd()
RAW_DIR = REPO_ROOT / "data" / "raw"

FILES = [
    ("CHANNEL_REGISTRY_RAW", RAW_DIR / "channel_registry.jsonl"),
    ("VIDEO_METADATA_RAW", RAW_DIR / "video_metadata.jsonl"),
    ("VIDEO_STATS_SNAPSHOTS_RAW", RAW_DIR / "video_stats_snapshots.jsonl"),
]

DB = "DATAEXPERT_STUDENT"
SCHEMA = "YOUTUBE_CAPSTONE"


def get_required(name: str) -> str:
    v = os.getenv(name)
    if v is None or v == "":
        raise ValueError(f"Missing required env var: {name}")
    return v


def connect():
    user = get_required("SNOWFLAKE_USER")
    acct = get_required("SNOWFLAKE_ACCOUNT")
    host = os.getenv("SNOWFLAKE_HOST")

    wh = get_required("SNOWFLAKE_WAREHOUSE")

    print(f"Using SNOWFLAKE_USER      = {user}")
    print(f"Using SNOWFLAKE_ACCOUNT   = {acct}")
    print(f"Using SNOWFLAKE_HOST      = {host or '(not set)'}")
    print(f"Using SNOWFLAKE_WAREHOUSE = {wh}")

    kwargs = dict(
        user=user,
        password=get_required("SNOWFLAKE_PASSWORD"),
        account=acct,
        role=os.getenv("SNOWFLAKE_ROLE"),
        database=DB,
        schema=SCHEMA,
    )

    if host:
        kwargs["host"] = host

    ctx = snowflake.connector.connect(**kwargs)

    cur = ctx.cursor()
    try:
        cur.execute("USE WAREHOUSE IDENTIFIER(%s)", (wh,))
        cur.execute("USE DATABASE IDENTIFIER(%s)", (DB,))
        cur.execute("USE SCHEMA IDENTIFIER(%s)", (SCHEMA,))
    finally:
        cur.close()

    return ctx

def load_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def insert_batch(cur, table: str, rows):
    """
    Insert a batch using a single statement:
      INSERT ... SELECT PARSE_JSON(v.$1), v.$2 FROM VALUES (...), (...), ...
    rows = [(json_string, filename), ...]
    """
    if not rows:
        return

    values_sql = ", ".join(["(%s, %s)"] * len(rows))

    params = []
    for j, f in rows:
        params.extend([j, f])

    sql = f"""
        INSERT INTO {DB}.{SCHEMA}.{table} (raw, source_file)
        SELECT PARSE_JSON(v.$1), v.$2
        FROM VALUES {values_sql} AS v
    """
    cur.execute(sql, params)


def main():
    print(f"Working dir: {Path.cwd()}")
    print(f"Raw dir    : {RAW_DIR}")

    ctx = connect()
    cur = ctx.cursor()
    try:
        for table, path in FILES:
            if not path.exists():
                print(f"\nSKIP {table}: missing file {path}")
                continue

            cur.execute(f"TRUNCATE TABLE {DB}.{SCHEMA}.{table}")
            print(f"\nTRUNCATED {DB}.{SCHEMA}.{table}")

            batch = []
            batch_size = 250  # keep under query size limits; bump later if you want

            for obj in load_jsonl(path):
                batch.append((json.dumps(obj), path.name))
                if len(batch) >= batch_size:
                    insert_batch(cur, table, batch)
                    ctx.commit()
                    batch = []

            if batch:
                insert_batch(cur, table, batch)
                ctx.commit()

            cur.execute(f"SELECT COUNT(*) FROM {DB}.{SCHEMA}.{table}")
            count = cur.fetchone()[0]
            print(f"LOADED {path.name} -> {table}: {count} rows")

        print("\nDone.")
    finally:
        try:
            cur.close()
        finally:
            ctx.close()


if __name__ == "__main__":
    main()