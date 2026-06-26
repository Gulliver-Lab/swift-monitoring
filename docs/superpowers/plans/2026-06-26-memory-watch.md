# memory-watch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a standalone `memory-watch` Python CLI that queries the Slurm accounting DB and lists jobs that requested at least 500 MiB but used at most 50% of that memory.

**Architecture:** Use a small pandas pipeline. `db.py` will fetch raw Slurm rows into a `DataFrame`, `memory.py` will normalize and filter memory fields, and `formatting.py` will print the final table. The CLI stays thin and only coordinates parsing, fetching, filtering, and printing.

**Tech Stack:** Python 3.14, `uv`, `pandas`, `mariadb`, `pytest`, `ruff`, `mypy`, `taskipy`

---

### Task 1: Scaffold the standalone package

**Files:**
- Create: `memory-watch/pyproject.toml`
- Create: `memory-watch/.python-version`
- Create: `memory-watch/src/memory_watch/__init__.py`
- Create: `memory-watch/src/memory_watch/cli.py`
- Create: `memory-watch/src/memory_watch/config.py`
- Create: `memory-watch/tests/test_cli.py`

- [ ] **Step 1: Write the failing test**

```python
from memory_watch.cli import build_parser


def test_build_parser_defines_required_dates():
    parser = build_parser()
    args = parser.parse_args(["--start", "2026-06-01", "--end", "2026-06-30"])
    assert args.start == "2026-06-01"
    assert args.end == "2026-06-30"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd memory-watch
uv run pytest tests/test_cli.py -v
```

Expected: import failure because `memory_watch.cli` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Create a minimal `pyproject.toml` with:

```toml
[project]
name = "memory-watch"
version = "0.1.0"
description = "Find Slurm jobs that used far less memory than requested"
readme = "README.md"
requires-python = ">=3.14"
dependencies = [
    "mariadb>=1.1.14",
    "pandas>=3.0.2",
]

[project.scripts]
memory-watch = "memory_watch.cli:main"

[dependency-groups]
dev = [
    "pytest",
    "ruff",
    "mypy",
    "taskipy",
]

[build-system]
requires = ["uv_build"]
build-backend = "uv_build"
```

Create a minimal CLI:

```python
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Find underused Slurm memory jobs")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    return parser


def main(argv: list[str] | None = None) -> None:
    build_parser().parse_args(argv)
```

Create the DB config helper:

```python
import os


def db_config() -> dict[str, str | int | None]:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "user": os.getenv("SLURM_DB_USER", "remote_user"),
        "password": os.getenv("SLURM_DB_PASSWORD"),
        "database": os.getenv("SLURM_DB_NAME", "slurm_acct_db"),
        "port": int(os.getenv("MARIADB_PORT", "3306")),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd memory-watch
uv run pytest tests/test_cli.py -v
```

Expected: pass.

### Task 2: Implement memory parsing and filtering

**Files:**
- Create: `memory-watch/src/memory_watch/memory.py`
- Create: `memory-watch/tests/test_memory.py`

- [ ] **Step 1: Write the failing test**

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
cd memory-watch
uv run pytest tests/test_memory.py -v
```

Expected: import failure or missing function failure.

- [ ] **Step 3: Write minimal implementation**

Implement:

```python
import re

import pandas as pd


_MEMORY_UNITS = {
    "K": 1024,
    "M": 1024**2,
    "G": 1024**3,
    "T": 1024**4,
    "P": 1024**5,
}


def parse_slurm_memory(value: str | None) -> int | None:
    if value is None:
        return None
    match = re.match(r"^\s*(\d+(?:\.\d+)?)([KMGTP]?)", value.upper())
    if match is None:
        return None
    number = float(match.group(1))
    unit = match.group(2) or "B"
    factor = _MEMORY_UNITS.get(unit, 1)
    return int(number * factor)


def filter_underused_jobs(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result = result.dropna(subset=["requested_bytes", "used_bytes"])
    result = result[result["requested_bytes"] >= 500 * 1024**2]
    result = result[result["used_bytes"] <= 0.5 * result["requested_bytes"]]
    result["usage_ratio"] = result["used_bytes"] / result["requested_bytes"]
    return result.sort_values("usage_ratio", ascending=True).reset_index(drop=True)


def enrich_with_memory_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result["requested_bytes"] = result["requested_mem"].map(parse_slurm_memory)
    result["used_bytes"] = result["max_rss"].map(parse_slurm_memory)
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```bash
cd memory-watch
uv run pytest tests/test_memory.py -v
```

Expected: pass.

### Task 3: Add DB loading and table formatting

**Files:**
- Create: `memory-watch/src/memory_watch/db.py`
- Create: `memory-watch/src/memory_watch/formatting.py`
- Create: `memory-watch/tests/test_db.py`
- Create: `memory-watch/tests/test_formatting.py`

- [ ] **Step 1: Write the failing tests**

```python
import pandas as pd

from memory_watch.formatting import format_jobs_table


def test_format_jobs_table_includes_expected_columns():
    df = pd.DataFrame(
        [
            {
                "user_name": "alice",
                "job_name": "test",
                "ended_at": "2026-06-01",
                "job_id": 42,
                "requested_bytes": 1024**3,
                "used_bytes": 400 * 1024**2,
                "usage_ratio": 0.4,
            }
        ]
    )
    output = format_jobs_table(df)
    assert "alice" in output
    assert "1.0 GiB" in output
    assert "400.0 MiB" in output
```

```python
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
    df = load_jobs_for_period(
        datetime(2026, 6, 1),
        datetime(2026, 6, 30),
    )

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
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
cd memory-watch
uv run pytest tests/test_formatting.py tests/test_db.py -v
```

Expected: missing module/function failures.

- [ ] **Step 3: Write minimal implementation**

Implement the DB layer around one connection helper from `config.py` and one query
function returning a pandas `DataFrame` with stable column names:

```python
def load_jobs_for_period(start: datetime, end: datetime) -> pd.DataFrame:
    conn = mariadb.connect(**db_config())
    query = f"""
    SELECT
        user_name,
        job_name,
        job_id,
        started_at,
        ended_at,
        requested_mem,
        max_rss
    FROM slurm_job_table
    WHERE started_at < {end.timestamp()}
      AND ended_at > {start.timestamp()}
    """
    return pd.read_sql_query(query, con=conn)
```

Implement the formatter with `DataFrame.to_string(index=False)` after renaming
the final columns to:

```python
["user", "date", "job_id", "job_name", "requested_memory", "used_memory", "usage_ratio"]
```

Use a helper like:

```python
def format_bytes(value: int | None) -> str:
    if value is None:
        return "-"
    if value >= 1024**3:
        return f"{value / 1024**3:.1f} GiB"
    return f"{value / 1024**2:.1f} MiB"


def format_jobs_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "No matching jobs"
    output = df.copy().rename(
        columns={
            "user_name": "user",
            "ended_at": "date",
            "job_id": "job_id",
            "job_name": "job_name",
            "requested_bytes": "requested_memory",
            "used_bytes": "used_memory",
        }
    )
    output["requested_memory"] = output["requested_memory"].map(format_bytes)
    output["used_memory"] = output["used_memory"].map(format_bytes)
    return output[
        ["user", "date", "job_id", "job_name", "requested_memory", "used_memory", "usage_ratio"]
    ].to_string(index=False)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
cd memory-watch
uv run pytest tests/test_db.py tests/test_formatting.py -v
```

Expected: pass.

### Task 4: Wire the CLI end to end

**Files:**
- Modify: `memory-watch/src/memory_watch/cli.py`
- Modify: `memory-watch/src/memory_watch/memory.py`
- Modify: `memory-watch/src/memory_watch/db.py`
- Modify: `memory-watch/src/memory_watch/formatting.py`
- Create: `memory-watch/README.md`

- [ ] **Step 1: Write the failing integration test**

```python
from memory_watch.cli import main


def test_main_renders_a_report(monkeypatch, capsys):
    monkeypatch.setattr(
        "memory_watch.cli.load_jobs_for_period",
        lambda start, end: __import__("pandas").DataFrame(
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
    monkeypatch.setattr(
        "memory_watch.cli.format_jobs_table",
        lambda df: "alice job",
    )
    main(["--start", "2026-06-01", "--end", "2026-06-30"])
    out = capsys.readouterr().out
    assert "alice" in out
```

- [ ] **Step 2: Run the integration test to verify it fails**

Run:

```bash
cd memory-watch
uv run pytest tests/test_cli.py -v
```

Expected: the report path is not wired yet.

- [ ] **Step 3: Write minimal implementation**

Wire `main()` so it:

1. parses `--start` and `--end`
2. calls the DB loader
3. converts memory columns to bytes
4. filters with the 500 MiB / 50% rule
5. prints the final table or a short "no matching jobs" message

Use this shape:

```python
from datetime import datetime, time


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    start = datetime.strptime(args.start, "%Y-%m-%d")
    end = datetime.strptime(args.end, "%Y-%m-%d")
    start = datetime.combine(start.date(), time.min)
    end = datetime.combine(end.date(), time.max)
    jobs = load_jobs_for_period(start, end)
    jobs = enrich_with_memory_columns(jobs)
    jobs = filter_underused_jobs(jobs)
    print(format_jobs_table(jobs))
```

Add a short README showing:

```bash
cd memory-watch
uv run memory-watch --start 2026-06-01 --end 2026-06-30
```

- [ ] **Step 4: Run the full test suite**

Run:

```bash
cd memory-watch
uv run pytest -v
uv run ruff check .
uv run ruff format --check .
```

Expected: all pass.

### Task 5: Review and request commit approval

**Files:**
- Inspect: all files under `memory-watch/`

- [ ] **Step 1: Review the diff**

Run:

```bash
git status --short
git diff -- memory-watch
```

- [ ] **Step 2: Ask for commit permission**

Do not commit yet. Ask the user before running `git commit`.
