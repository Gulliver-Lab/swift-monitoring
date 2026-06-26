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
_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalize_column_name(name: str) -> str:
    return _NORMALIZE_PATTERN.sub("", name.casefold())


def _resolve_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    normalized_lookup = {
        _normalize_column_name(column): column for column in df.columns
    }
    for alias in aliases:
        column = normalized_lookup.get(_normalize_column_name(alias))
        if column is not None:
            return column
    return None


def normalize_job_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    rename: dict[str, str] = {}
    for canonical, aliases in JOB_COLUMN_ALIASES.items():
        column = _resolve_column(result, aliases)
        if column is not None:
            rename[column] = canonical
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
    requested_column = _resolve_column(result, JOB_COLUMN_ALIASES["requested_mem"])
    used_column = _resolve_column(result, JOB_COLUMN_ALIASES["max_rss"])
    if requested_column is None:
        raise KeyError("Missing requested memory column")
    if used_column is None:
        raise KeyError("Missing used memory column")
    result["requested_bytes"] = result[requested_column].map(parse_slurm_memory)
    result["used_bytes"] = result[used_column].map(parse_slurm_memory)
    return result


def filter_underused_jobs(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result = result.dropna(subset=["requested_bytes", "used_bytes"])
    result = result[result["requested_bytes"] >= MEMORY_MIN_BYTES]
    result = result[result["used_bytes"] <= 0.5 * result["requested_bytes"]]
    result = result.assign(usage_ratio=result["used_bytes"] / result["requested_bytes"])
    return result.sort_values("usage_ratio", ascending=True).reset_index(drop=True)
