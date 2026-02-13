from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Iterable


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def ensure_parent_dir(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def write_jsonl(path: str, rows: Iterable[dict[str, Any]]) -> int:
    """
    Write rows to a JSON Lines file (append).
    Returns number of rows written.
    """
    ensure_parent_dir(path)
    count = 0

    with open(path, "a", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            count += 1

    return count