from __future__ import annotations

import pandas as pd


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

    output = df.copy()
    if "ended_at" in output.columns:
        output["date"] = pd.to_datetime(output["ended_at"]).dt.strftime("%Y-%m-%d")
    elif "started_at" in output.columns:
        output["date"] = pd.to_datetime(output["started_at"]).dt.strftime("%Y-%m-%d")
    else:
        output["date"] = "-"

    output = output.rename(
        columns={
            "user_name": "user",
            "job_name": "job_name",
            "job_id": "job_id",
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
        "date",
        "job_id",
        "job_name",
        "requested_memory",
        "used_memory",
        "usage_ratio",
    ]
    return output[columns].to_string(index=False)
