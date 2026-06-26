from datetime import datetime

import pandas as pd

from memory_watch.db import load_jobs_for_period


def test_load_jobs_for_period_uses_expected_query(monkeypatch):
    captured = {}

    class FakeConnection:
        pass

    def fake_connect(**kwargs):
        captured["connect"] = kwargs
        return FakeConnection()

    def fake_read_sql_query(query, con):
        captured["query"] = query
        captured["connection"] = con
        return pd.DataFrame(
            [
                {
                    "user": "alice",
                    "job_name": "job",
                    "id_job": 42,
                    "time_start": 1717200000,
                    "time_end": 1717286400,
                    "mem_req": "1G",
                    "tres_req": "cpu=2,mem=1G,node=1",
                    "tres_usage_in_max": "1=25,2=6369280,3=0,6=0,7=0,8=0",
                }
            ]
        )

    monkeypatch.setattr("memory_watch.db.mariadb.connect", fake_connect)
    monkeypatch.setattr("memory_watch.db.pd.read_sql_query", fake_read_sql_query)

    df = load_jobs_for_period(datetime(2026, 6, 1), datetime(2026, 6, 30))

    assert captured["connection"].__class__.__name__ == "FakeConnection"
    assert "FROM" in captured["query"].upper()
    assert list(df.columns) == [
        "user",
        "job_name",
        "id_job",
        "time_start",
        "time_end",
        "mem_req",
        "tres_req",
        "tres_usage_in_max",
    ]
