from __future__ import annotations

import argparse
from datetime import datetime, time
from typing import Sequence

from memory_watch.db import load_jobs_for_period
from memory_watch.formatting import format_jobs_table
from memory_watch.memory import enrich_with_memory_columns, filter_underused_jobs


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Find Slurm jobs that used much less memory than requested"
    )
    parser.add_argument("--start", required=True, help="Start date in YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="End date in YYYY-MM-DD")
    return parser


def _parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    start = datetime.combine(_parse_date(args.start).date(), time.min)
    end = datetime.combine(_parse_date(args.end).date(), time.max)
    jobs = load_jobs_for_period(start, end)
    jobs = enrich_with_memory_columns(jobs)
    jobs = filter_underused_jobs(jobs)
    print(format_jobs_table(jobs))
