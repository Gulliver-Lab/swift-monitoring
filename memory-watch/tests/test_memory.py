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
    df = pd.DataFrame([{"mem_req": "1G", "tres_usage_in_max": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_slurm_casing():
    df = pd.DataFrame([{"ReqMem": "1G", "Tres_Usage_In_Max": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_tres_request_strings():
    df = pd.DataFrame(
        [{"tres_req": "cpu=2,mem=1G,node=1", "tres_usage_in_max": "400M"}]
    )
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_suffixed_rss_columns():
    df = pd.DataFrame([{"mem_req": "1G", "tres_usage_in_max_nodeid": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2


def test_enrich_with_memory_columns_handles_rss_like_columns():
    df = pd.DataFrame([{"mem_req": "1G", "peakrss": "400M"}])
    result = enrich_with_memory_columns(df)
    assert result.iloc[0]["requested_bytes"] == 1024**3
    assert result.iloc[0]["used_bytes"] == 400 * 1024**2
