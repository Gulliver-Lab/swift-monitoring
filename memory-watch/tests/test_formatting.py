import pandas as pd

from memory_watch.formatting import format_jobs_table


def test_format_jobs_table_includes_expected_values():
    df = pd.DataFrame(
        [
            {
                "user": "alice",
                "job_name": "test",
                "job_id": 42,
                "time_start": 1000,
                "time_end": 4661,
                "requested_bytes": 1024**3,
                "used_bytes": 400 * 1024**2,
                "usage_ratio": 0.4,
            }
        ]
    )
    output = format_jobs_table(df)
    assert "alice" in output
    assert "1h 1m 1s" in output
    assert "1.0 GiB" in output
    assert "400.0 MiB" in output
    assert "0.40" in output
