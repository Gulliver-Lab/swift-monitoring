# memory-watch Design

## Goal

Create a new standalone Python package in `memory-watch/` named `memory-watch`.
It will provide a simple CLI that queries the Slurm accounting database for jobs
that requested much more memory than they actually used.

The tool will:

- accept a start date and end date
- query the Slurm accounting DB for jobs in that interval
- compare requested memory against peak used memory at the job level
- flag jobs where:
  - requested memory is at least 250 MiB
  - peak used memory is at most 50% of requested memory
- print a terminal table with basic job metadata

## Non-Goals

- No reuse of the existing `usage-reports` Python modules
- No PDF or graphical output
- No per-step or per-task memory analysis
- No automatic remediation or notifications
- No attempt to infer ideal request sizes

## Package Layout

The package will follow the same general setup as `usage-reports`:

- `memory-watch/pyproject.toml`
- `memory-watch/uv.lock`
- `memory-watch/.python-version`
- `memory-watch/src/memory_watch/`

Suggested modules:

- `memory_watch/cli.py` - argument parsing and top-level command
- `memory_watch/config.py` - DB connection settings from environment variables
- `memory_watch/db.py` - Slurm accounting query and raw `DataFrame` loading
- `memory_watch/memory.py` - memory parsing, normalization, and filtering
- `memory_watch/models.py` - typed row/schema helpers if needed
- `memory_watch/formatting.py` - terminal table formatting

## CLI

The CLI will expose a single command:

```bash
uv run memory-watch --start YYYY-MM-DD --end YYYY-MM-DD
```

Arguments:

- `--start`: required, inclusive start date
- `--end`: required, inclusive end date

Optional configuration will come from environment variables, matching the
pattern already used in `usage-reports`:

- `DB_HOST`
- `MARIADB_PORT`
- `SLURM_DB_USER`
- `SLURM_DB_PASSWORD`
- `SLURM_DB_NAME`

## Data Source

The program will query the Slurm accounting database directly, using a SQL
query that returns the job-level fields needed for the report.

The implementation should rely on the fields already exposed by the Slurm
accounting schema, with the expectation that the following are available or
equivalent:

- job id
- user name
- job name
- submit or start/end timestamp
- requested memory
- peak memory used by the job
- job state

The exact column names should be isolated in the DB layer so they can be
adjusted without changing the rest of the pipeline.

## Memory Normalization

Slurm memory values may appear with units or in different field encodings.
The pipeline will normalize both requested and used memory to bytes before
comparison.

Rules:

- parse Slurm-style memory strings into bytes
- preserve missing values as nulls
- ignore rows where requested or used memory cannot be parsed
- compare using bytes only

Threshold rule:

- a job is flagged when `used_bytes <= 0.5 * requested_bytes`
- but only if `requested_bytes >= 250 * 1024 * 1024`

This means small jobs are intentionally ignored even when they show large
relative underuse.

## Pandas Pipeline

The implementation will use a pandas-first pipeline:

1. fetch raw rows from the DB into a `DataFrame`
2. normalize memory columns into bytes
3. filter to completed jobs in the date range
4. apply the underuse threshold
5. sort by greatest underuse first
6. print a compact table

This keeps the logic easy to inspect and allows straightforward testing of
intermediate columns.

## Output

The CLI will print a table with one row per flagged job.

Required columns:

- user
- date
- job id
- job name
- requested memory
- peak used memory
- used/requested ratio

Formatting requirements:

- human-readable memory units in output
- stable column order
- sorted by lowest used/requested ratio first
- no output if no jobs match, aside from a short informational message

## Error Handling

The CLI should fail clearly for:

- missing or malformed dates
- database connection failures
- empty or malformed memory fields in a way that prevents parsing

Expected behavior:

- dates are validated at parse time
- DB errors should produce a concise error message and non-zero exit status
- unparsable rows are skipped rather than crashing the report

## Testing

Minimum tests:

- CLI argument parsing
- memory string parsing
- threshold filtering
- output formatting for one or more example rows
- DB query function with a mocked connection or fixture `DataFrame`

Test focus:

- correctness of the 50% / 250 MiB rule
- correctness of byte normalization
- stability of the printed columns

## Acceptance Criteria

The work is complete when:

- `memory-watch/` exists as a standalone `uv`-managed package
- the CLI accepts `--start` and `--end`
- the program queries the Slurm accounting DB
- the program prints jobs that satisfy the agreed underuse rule
- the implementation is separate from `usage-reports`

