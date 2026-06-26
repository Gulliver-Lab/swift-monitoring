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


def format_jobs_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "No matching jobs"

    output = normalize_job_columns(df)

    output = output.rename(
        columns={
            "requested_bytes": "requested_memory",
            "used_bytes": "used_memory",
        }
    )
    output["requested_memory"] = output["requested_memory"].map(format_bytes)
    output["used_memory"] = output["used_memory"].map(format_bytes)
    output["usage_ratio"] = output["usage_ratio"].map(
        lambda value: "-" if pd.isna(value) else f"{float(value):.2f}"
    )

    columns = [
        "user",
        "duration",
        "id_job",
        "job_name",
        "requested_memory",
        "used_memory",
        "usage_ratio",
    ]
    return output[columns].to_string(index=False)
