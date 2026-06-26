# memory-watch

CLI to find Slurm jobs that requested much more memory than they used.

```bash
ssh -L 3307:localhost:3306 root@head # forward MariaDB's port to localhost:3307
MARIADB_PORT=3307 SLURM_DB_PASSWORD=xxx uv run memory-watch --start 2026-06-20 --end 2026-06-26
```
