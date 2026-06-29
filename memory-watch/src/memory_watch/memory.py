from __future__ import annotations

import pandas as pd

MIN_OVER_PROVISION_BYTES = 500 * 1024**2  # 500M


def _parse_memory_cell(value: object) -> int | None:
    if value is None or value is pd.NA:
        return None
    text = str(value)
    if text == "":
        return None
    return int(text.split(",")[1].split("=")[1])


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
