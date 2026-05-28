from datetime import datetime

import mariadb  # type: ignore
import pandas as pd

from reports.settings import db_config
from reports.utils import get_gpu_info, trim_df_between_dates


def get_raw_data_for_time_period(start_date: datetime, end_date: datetime):
    conn = None
    try:
        conn = mariadb.connect(**db_config)

        # Unfinished jobs have a time_end equal to zero
        query = f"""
        SELECT
            *
        FROM
            default_job_table
        WHERE
            time_start < {end_date.timestamp()} AND time_start > 0 AND (time_end > {start_date.timestamp()} OR time_end = 0);
        """  # noqa: E501

        df = pd.read_sql(query, con=conn)
        conn.close()

    except mariadb.Error as e:
        print(f"Database error: {e}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if conn and is_connected(conn):
            conn.close()

    df = trim_df_between_dates(df, start_date, end_date)
    df["GPU"] = get_gpu_info(df)

    return df


def is_connected(conn):
    try:
        conn.ping()
    except:  # noqa: E722
        return False
    return True
