import pandas as pd

from memory_watch.memory import (
    enrich_with_memory_columns,
    filter_underused_jobs,
    parse_slurm_memory,
)


def test_parse_slurm_memory_handles_slurm_units():
    assert parse_slurm_memory("1G") == 1024**3
    assert parse_slurm_memory("512M") == 512 * 1024**2


def test_filter_underused_jobs_applies_500m_and_50_percent_rule():
    df = pd.DataFrame(
        [
            {"requested_bytes": 1024**3, "used_bytes": 400 * 1024**2},
            {"requested_bytes": 100 * 1024**2, "used_bytes": 40 * 1024**2},
        ]
    )
    result = filter_underused_jobs(df)
    assert len(result) == 1
    assert result.iloc[0]["requested_bytes"] == 1024**3


def test_enrich_with_memory_columns_parses_requested_and_used_memory():
    df = pd.DataFrame([{"requested_mem": "1G", "max_rss": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_slurm_casing():
    df = pd.DataFrame([{"ReqMem": "1G", "MaxRSS": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_tres_request_strings():
    df = pd.DataFrame([{"ReqTRES": "cpu=2,mem=1G,node=1", "MaxRSS": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_suffixed_rss_columns():
    df = pd.DataFrame([{"ReqMem": "1G", "MaxRSSNode": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_rss_like_columns():
    df = pd.DataFrame([{"ReqMem": "1G", "PeakRSS": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2
