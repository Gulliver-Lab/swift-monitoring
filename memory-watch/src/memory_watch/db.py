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
        SELECT *
        FROM default_job_table
        WHERE time_end > {start.timestamp()}
          AND time_end <= {end.timestamp()}
        """
        return pd.read_sql_query(query, con=conn)
    finally:
        if conn is not None:
            close = getattr(conn, "close", None)
            if callable(close):
                close()
