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
            j.id_job,
            u.name AS `user`,
            j.job_name,
            j.time_start,
            j.time_end,
            j.mem_req,
            j.tres_req,
            s.tres_usage_in_max,
            s.tres_usage_in_max_nodeid,
            s.tres_usage_in_max_taskid
        FROM default_job_table AS j
        INNER JOIN user_table AS u
            ON j.id_user = u.id_user
        INNER JOIN default_step_table AS s
            ON j.job_db_inx = s.job_db_inx
           AND s.id_step = -5
        WHERE j.time_end > {start.timestamp()}
          AND j.time_end <= {end.timestamp()}
        """
        return pd.read_sql_query(query, con=conn)
    finally:
        if conn is not None:
            close = getattr(conn, "close", None)
            if callable(close):
                close()
