from __future__ import annotations

import re

import pandas as pd

MEMORY_MIN_BYTES = 500 * 1024**2

JOB_COLUMN_ALIASES = {
    "user": ["user", "user_name"],
    "job_name": ["job_name", "jobname"],
    "job_id": ["job_id", "jobid"],
    "started_at": ["started_at", "time_start"],
    "ended_at": ["ended_at", "time_end"],
    "requested_mem": ["requested_mem", "reqmem", "req_mem"],
    "max_rss": ["max_rss", "maxrss"],
}

_MEMORY_UNITS = {
    "": 1,
    "B": 1,
    "K": 1024,
    "M": 1024**2,
    "G": 1024**3,
    "T": 1024**4,
    "P": 1024**5,
}

_SLURM_MEMORY_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+)?)([BKMGTP]?)\s*$", re.IGNORECASE)


def normalize_job_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    rename: dict[str, str] = {}
    for canonical, aliases in JOB_COLUMN_ALIASES.items():
        for alias in aliases:
            if alias in result.columns:
                rename[alias] = canonical
                break
    return result.rename(columns=rename)


def parse_slurm_memory(value: str | int | float | None) -> int | None:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (int, float)):
        return int(value)

    match = _SLURM_MEMORY_PATTERN.match(str(value))
    if match is None:
        return None

    amount = float(match.group(1))
    unit = match.group(2).upper()
    return int(amount * _MEMORY_UNITS[unit])


def enrich_with_memory_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = normalize_job_columns(df)
    result["requested_bytes"] = result["requested_mem"].map(parse_slurm_memory)
    result["used_bytes"] = result["max_rss"].map(parse_slurm_memory)
    return result


def filter_underused_jobs(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result = result.dropna(subset=["requested_bytes", "used_bytes"])
    result = result[result["requested_bytes"] >= MEMORY_MIN_BYTES]
    result = result[result["used_bytes"] <= 0.5 * result["requested_bytes"]]
    result = result.assign(usage_ratio=result["used_bytes"] / result["requested_bytes"])
    return result.sort_values("usage_ratio", ascending=True).reset_index(drop=True)
