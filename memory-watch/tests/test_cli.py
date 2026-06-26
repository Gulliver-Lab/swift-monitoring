import pandas as pd

from memory_watch.cli import build_parser, main


def test_build_parser_defines_required_dates():
    parser = build_parser()
    args = parser.parse_args(["--start", "2026-06-01", "--end", "2026-06-30"])
    assert args.start == "2026-06-01"
    assert args.end == "2026-06-30"


def test_main_renders_a_report(monkeypatch, capsys):
    monkeypatch.setattr(
        "memory_watch.cli.load_jobs_for_period",
        lambda start, end: pd.DataFrame(
            [
                {
                    "user_name": "alice",
                    "job_name": "job",
                    "job_id": 42,
                    "started_at": "2026-06-01",
                    "ended_at": "2026-06-01",
                    "requested_mem": "1G",
                    "max_rss": "400M",
                }
            ]
        ),
    )
    monkeypatch.setattr("memory_watch.cli.format_jobs_table", lambda df: "alice job")

    main(["--start", "2026-06-01", "--end", "2026-06-30"])

    out = capsys.readouterr().out
    assert "alice" in out
