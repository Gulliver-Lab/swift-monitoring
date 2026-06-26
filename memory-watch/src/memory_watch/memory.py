from __future__ import annotations

import re

import pandas as pd

MEMORY_MIN_BYTES = 1000 * 1024**2

JOB_COLUMN_ALIASES = {
    "user": ["user", "user_name"],
    "job_name": ["job_name", "jobname"],
    "job_id": ["job_id", "jobid"],
    "started_at": ["started_at", "time_start"],
    "ended_at": ["ended_at", "time_end"],
    "requested_mem": ["requested_mem", "mem_req", "reqmem", "req_mem"],
    "tres_req": ["tres_req", "reqtres", "req_tres"],
    "tres_usage_in_max": [
        "tres_usage_in_max",
        "max_rss",
        "maxrss",
        "max_rss_node",
        "max_rss_task",
        "peak_rss",
        "peakrss",
        "rss_max",
        "rssmax",
    ],
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

_SLURM_MEMORY_PATTERN = re.compile(
    r"^\s*(\d+(?:\.\d+)?)([BKMGTP]?)(?:[a-zA-Z]*)\s*$", re.IGNORECASE
)
_TRES_MEMORY_PATTERN = re.compile(r"(?:^|[, ])mem=([^, ]+)", re.IGNORECASE)
_NORMALIZE_PATTERN = re.compile(r"[^a-z0-9]+")


def _normalize_column_name(name: str) -> str:
    return _NORMALIZE_PATTERN.sub("", name.casefold())


def _resolve_column(df: pd.DataFrame, aliases: list[str]) -> str | None:
    normalized_lookup = {
        _normalize_column_name(column): column for column in df.columns
    }
    for alias in aliases:
        normalized_alias = _normalize_column_name(alias)
        column = normalized_lookup.get(normalized_alias)
        if column is not None:
            return column
        for normalized_column, original_column in normalized_lookup.items():
            if (
                normalized_alias in normalized_column
                or normalized_column in normalized_alias
            ):
                return original_column
    return None


def _resolve_requested_column(df: pd.DataFrame) -> str | None:
    column = _resolve_column(df, JOB_COLUMN_ALIASES["requested_mem"])
    if column is not None:
        return column

    tres_column = _resolve_column(df, JOB_COLUMN_ALIASES["tres_req"])
    if tres_column is not None:
        return tres_column

    for original_column in df.columns:
        normalized = _normalize_column_name(original_column)
        if "reqtres" == normalized:
            return original_column
    return None


def _resolve_used_column(df: pd.DataFrame) -> str | None:
    column = _resolve_column(df, JOB_COLUMN_ALIASES["tres_usage_in_max"])
    if column is not None:
        return column

    for original_column in df.columns:
        normalized = _normalize_column_name(original_column)
        if (
            "tresusageinmax" in normalized
            or "maxrss" in normalized
            or "peakrss" in normalized
        ):
            return original_column
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


def _parse_memory_cell(value: object) -> int | None:
    if value is None or value is pd.NA:
        return None
    text = str(value)
    if text == "":
        return None
    return float(text.split(",")[1].split("=")[1])


def _parse_requested_memory(value: object) -> int | None:
    if value is None or value is pd.NA:
        return None
    text = str(value)
    tres_match = _TRES_MEMORY_PATTERN.search(text)
    if tres_match is not None:
        return parse_slurm_memory(tres_match.group(1))
    return parse_slurm_memory(text)


def enrich_with_memory_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = normalize_job_columns(df)
    requested_column = _resolve_requested_column(result)
    used_column = _resolve_used_column(result)
    if requested_column is None:
        raise KeyError("Missing requested memory column")
    if used_column is None:
        raise KeyError(
            "Missing used memory column; available columns: "
            f"{', '.join(map(str, result.columns))}"
        )
    result["requested_bytes"] = result[requested_column] * 1024**2
    result["used_bytes"] = result[used_column].map(_parse_memory_cell)
    return result


def filter_underused_jobs(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result = result.dropna(subset=["requested_bytes", "used_bytes"])
    result = result[result["requested_bytes"] >= MEMORY_MIN_BYTES]
    result = result[result["used_bytes"] <= 0.5 * result["requested_bytes"]]
    result = result.assign(usage_ratio=result["used_bytes"] / result["requested_bytes"])
    return result.sort_values("usage_ratio", ascending=True).reset_index(drop=True)
