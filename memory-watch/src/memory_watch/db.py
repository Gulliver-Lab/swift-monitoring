from __future__ import annotations

from datetime import datetime

import mariadb
import pandas as pd

from memory_watch.config import db_config


def load_jobs_for_period(start: datetime, end: datetime) -> pd.DataFrame:
    conn = None
    try:
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
        FROM default_job_table
        WHERE started_at < {end.timestamp()}
          AND ended_at > {start.timestamp()}
        """
        return pd.read_sql_query(query, con=conn)
    finally:
        if conn is not None:
            close = getattr(conn, "close", None)
            if callable(close):
                close()
