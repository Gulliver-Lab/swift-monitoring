from __future__ import annotations

import pandas as pd

from memory_watch.memory import normalize_job_columns


def format_bytes(value: int | float | None) -> str:
    if value is None or pd.isna(value):
        return "-"
    size = float(value)
    if size >= 1024**3:
        return f"{size / 1024**3:.1f} GiB"
    return f"{size / 1024**2:.1f} MiB"


def format_duration(value: int | float | None) -> str:
    if value is None or pd.isna(value):
        return "-"

    total_seconds = int(value)
    if total_seconds < 0:
        return "-"

    days, remainder = divmod(total_seconds, 24 * 3600)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)

    parts: list[str] = []
    if days:
        parts.append(f"{days}d")
    if hours or parts:
        parts.append(f"{hours}h")
    if minutes or parts:
        parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)


def _to_datetime(series: pd.Series) -> pd.Series:
    if pd.api.types.is_numeric_dtype(series):
        return pd.to_datetime(series, unit="s", errors="coerce")
    return pd.to_datetime(series, errors="coerce")


def format_jobs_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "No matching jobs"

    output = (
        normalize_job_columns(df)
        .sort_values(by="over_provision")
        .reset_index(drop=True)
    )

    output = output.rename(
        columns={
            "requested_bytes": "requested_memory",
            "used_bytes": "used_memory",
        }
    )
    output["requested_memory"] = output["requested_memory"].map(format_bytes)
    output["used_memory"] = output["used_memory"].map(format_bytes)
    output["over_provision"] = output["over_provision"].map(format_bytes)
    output["duration"] = output["duration"].map(format_duration)
    output["usage_ratio"] = output["usage_ratio"].map(
        lambda value: "-" if pd.isna(value) else f"{float(value):.2f}"
    )

    output.drop_duplicates(subset=["user", "job_name", "usage_ratio"], inplace=True)

    columns = [
        "user",
        "duration",
        "id_job",
        "job_name",
        "requested_memory",
        "used_memory",
        "over_provision",
        "usage_ratio",
    ]
    return output[columns].to_string(index=False)
