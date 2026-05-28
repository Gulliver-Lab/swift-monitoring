from datetime import datetime

import pandas as pd

from reports.settings import gpu_per_node


def trim_df_between_dates(
    df: pd.DataFrame, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    df = df.copy()
    # For unfinished jobs, set the end time to the limit of our bounds
    df.loc[df["time_end"] == 0, "time_end"] = end_date.timestamp()
    # For jobs that finished after our highest bound, set the end time this bound
    df.loc[df["time_end"] > end_date.timestamp(), "time_end"] = end_date.timestamp()
    # For jobs that started before our lowest bound, set the start to this bound
    df.loc[df["time_start"] < start_date.timestamp(), "time_start"] = (
        start_date.timestamp()
    )

    df["duration"] = df["time_end"] - df["time_start"]
    assert df["duration"].max() <= (end_date - start_date).total_seconds()

    return df[df["duration"] > 0].reset_index(drop=True)


def get_gpu_info(ddf: pd.DataFrame) -> pd.Series:
    return pd.Series(
        [
            gpu_per_node[nodelist] if "1001=" in tres_req else None
            for tres_req, nodelist in zip(ddf["tres_req"], ddf["nodelist"])
        ],
        name="GPU",
    )
