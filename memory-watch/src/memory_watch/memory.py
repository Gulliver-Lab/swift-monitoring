from __future__ import annotations

import re

import pandas as pd

MIN_OVER_PROVISION_BYTES = 500 * 1024**2  # 500M

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


def _parse_memory_cell(value: object) -> int | None:
    if value is None or value is pd.NA:
        return None
    text = str(value)
    if text == "":
        return None
    return float(text.split(",")[1].split("=")[1])


def enrich_with_memory_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()

    result["requested_bytes"] = result["mem_req"] * 1024**2
    result["used_bytes"] = result["tres_usage_in_max"].map(_parse_memory_cell)
    result["over_provision"] = result["requested_bytes"] - result["used_bytes"]
    return result


def filter_underused_jobs(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result = result.dropna(subset=["requested_bytes", "used_bytes"])
    result = result[result["over_provision"] >= MIN_OVER_PROVISION_BYTES]
    result = result[result["used_bytes"] <= 0.5 * result["requested_bytes"]]
    result = result.assign(usage_ratio=result["used_bytes"] / result["requested_bytes"])
    return result.sort_values("usage_ratio", ascending=True).reset_index(drop=True)
