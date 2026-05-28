# Usage-Reports

Small Python package to generate graphical reports of the cluster usage, in PDF.

## Usage

The [settings.py](./src/reports/settings.py) file contains the information to connect to
the slurm accounting database. It's fetched from env variable, with defaults that match
our cluster's settings.
The CPU/GPU info per partition/node is also hardcoded in this file, which is used to
compute usage percentages.

This package is managed with `uv`, so the preferred way of running it is with `uv run`:
```bash
SLURM_DB_PASSWORD=xxx uv run src/reports/main.py --start 2026-03-01 --end 2026-03-31 --output report.pdf
```

You can run this command from a machine different than the one running the slurm accounting
db, by forwarding the proper port over ssh.
For instance:
```bash
ssh -L 3307:localhost:3306 root@head # forward MariaDB's port to localhost:3307
MARIADB_PORT=3307 SLURM_DB_PASSWORD=xxx uv run src/reports/main.py --start 2026-03-01 --end 2026-03-31 --output report.pdf
```
