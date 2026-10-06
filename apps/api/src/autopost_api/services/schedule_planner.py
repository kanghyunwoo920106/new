from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Iterable

INTERVAL_SECONDS = {
    "4h": 4 * 3600,
    "12h": 12 * 3600,
    "24h": 24 * 3600,
    "1d": 24 * 3600,
    "2d": 2 * 24 * 3600,
    "1w": 7 * 24 * 3600,
}

ALLOWED_INTERVALS = ("4h", "12h", "24h", "2d", "1w")


def normalize_intervals(codes: Iterable[str]) -> list[str]:
    out: list[str] = []
    for c in codes:
        code = "24h" if c == "1d" else c
        if code not in INTERVAL_SECONDS:
            raise ValueError(f"unsupported interval: {c}")
        if code not in out:
            out.append(code)
    if not out:
        raise ValueError("at least one interval required for scheduled mode")
    return sorted(out, key=lambda x: INTERVAL_SECONDS[x])


def plan_run_times(
    *,
    first_publish_at: datetime,
    count: int,
    interval_codes: list[str],
    mode: str = "sequential_cycle",
) -> list[datetime]:
    if count <= 0:
        return []
    if first_publish_at.tzinfo is None:
        first_publish_at = first_publish_at.replace(tzinfo=timezone.utc)

    if mode != "sequential_cycle":
        raise NotImplementedError("only sequential_cycle in Phase 1")

    codes = normalize_intervals(interval_codes)
    times = [first_publish_at]
    if count == 1:
        return times

    cursor = first_publish_at
    i = 0
    while len(times) < count:
        delta = INTERVAL_SECONDS[codes[i % len(codes)]]
        cursor = cursor + timedelta(seconds=delta)
        times.append(cursor)
        i += 1
    return times
