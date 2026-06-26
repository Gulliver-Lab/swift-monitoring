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
                    "user_name": "alice",
                    "job_name": "job",
                    "job_id": 42,
                    "started_at": 1717200000,
                    "ended_at": 1717286400,
                    "requested_mem": "1G",
                    "max_rss": "400M",
                }
            ]
        )

    monkeypatch.setattr("memory_watch.db.mariadb.connect", fake_connect)
    monkeypatch.setattr("memory_watch.db.pd.read_sql_query", fake_read_sql_query)

    df = load_jobs_for_period(datetime(2026, 6, 1), datetime(2026, 6, 30))

    assert captured["connection"].__class__.__name__ == "FakeConnection"
    assert "FROM" in captured["query"].upper()
    assert list(df.columns) == [
        "user_name",
        "job_name",
        "job_id",
        "started_at",
        "ended_at",
        "requested_mem",
        "max_rss",
    ]
