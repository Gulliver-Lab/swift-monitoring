from __future__ import annotations

from datetime import datetime

import mariadb
import pandas as pd

from memory_watch.config import db_config

MIN_DURATION_SECOND = 300  # 5 minutes


def load_jobs_for_period(start: datetime, end: datetime) -> pd.DataFrame:
    conn = None
    try:
        conn = mariadb.connect(**db_config())
        query = f"""
        SELECT
            j.id_job,
            a.user AS `user`,
            j.job_name,
            j.time_start,
            j.time_end,
            j.mem_req,
            j.tres_req,
            j.cpus_req,
            s.tres_usage_in_max,
            s.tres_usage_in_max_nodeid,
            s.tres_usage_in_max_taskid
        FROM default_job_table AS j
        INNER JOIN default_assoc_table AS a
            ON j.id_assoc = a.id_assoc
        INNER JOIN default_step_table AS s
            ON j.job_db_inx = s.job_db_inx
           AND s.id_step = -5
        WHERE j.time_end > {start.timestamp()}
          AND j.time_end <= {end.timestamp()}
        """
        df = pd.read_sql_query(query, con=conn)
        df["duration"] = df["time_end"] - df["time_start"]
        return df[df["duration"] > MIN_DURATION_SECOND]
    finally:
        if conn is not None:
            close = getattr(conn, "close", None)
            if callable(close):
                close()
