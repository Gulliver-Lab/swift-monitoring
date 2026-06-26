from __future__ import annotations

import os


def db_config() -> dict[str, str | int | None]:
    return {
        "host": os.getenv("DB_HOST", "127.0.0.1"),
        "user": os.getenv("SLURM_DB_USER", "remote_user"),
        "password": os.getenv("SLURM_DB_PASSWORD"),
        "database": os.getenv("SLURM_DB_NAME", "slurm_acct_db"),
        "port": int(os.getenv("MARIADB_PORT", "3306")),
    }
