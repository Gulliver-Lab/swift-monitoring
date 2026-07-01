from datetime import datetime, time, timedelta

import pandas as pd

from reports.data import get_raw_data_for_time_period
from reports.settings import (
    cpus_per_partition,
    gpu_per_node,
    id_qos_name,
    ram_per_partition_gb,
)
from reports.utils import trim_df_between_dates


def get_available_cpu_for_period(
    start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    seconds_for_this_period = (end_date - start_date).total_seconds()
    df_cpu = (
        pd.DataFrame([cpus_per_partition])
        .T.reset_index()
        .rename(columns={0: "CPUs", "index": "partition"})
    )
    df_cpu["available"] = df_cpu["CPUs"] * seconds_for_this_period
    return df_cpu[["partition", "available"]]


def get_available_ram_for_period(
    start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    seconds_for_this_period = (end_date - start_date).total_seconds()
    df_ram = (
        pd.DataFrame([ram_per_partition_gb])
        .T.reset_index()
        .rename(columns={0: "RAM", "index": "partition"})
    )
    df_ram["available"] = df_ram["RAM"] * seconds_for_this_period
    return df_ram[["partition", "available"]]


def get_available_gpu_for_period(
    start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    seconds_for_this_period = (end_date - start_date).total_seconds()

    df_gpu = (
        pd.DataFrame([gpu_per_node])
        .T.rename(columns={0: "GPU"})
        .reset_index()
        .groupby("GPU")
        .count()
        .reset_index()
    )
    df_gpu["available"] = df_gpu["index"] * seconds_for_this_period

    return df_gpu[["GPU", "available"]]


def get_cpu_load(
    ddf: pd.DataFrame, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    ddf = ddf[ddf["GPU"].isna()].copy()
    if ddf.empty:
        return pd.DataFrame()

    ddf["consumption"] = ddf["duration"] * ddf["cpus_req"]
    df_usage_partition = (
        ddf.groupby(["partition"])
        .apply(lambda x: sum(x["consumption"]))
        .rename("consumption")
        .reset_index()
        .merge(get_available_cpu_for_period(start_date, end_date), how="right")
        .fillna(0)
    )
    vals = dict(df_usage_partition.sum())
    vals["partition"] = "total"
    df_usage_partition = pd.concat([df_usage_partition, pd.DataFrame([vals])])

    df_usage_partition["load"] = (
        df_usage_partition["consumption"] / df_usage_partition["available"]
    )

    return df_usage_partition[["partition", "load"]]


def get_gpu_load(
    ddf: pd.DataFrame, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    ddf = ddf[~ddf["GPU"].isna()].copy()
    if ddf.empty:
        return pd.DataFrame()

    df_usage_partition = (
        ddf.groupby("GPU")
        .apply(lambda x: sum(x["duration"]))
        .rename("consumption")
        .reset_index()
        .merge(get_available_gpu_for_period(start_date, end_date), how="right")
        .fillna(0)
    )
    vals = dict(df_usage_partition.sum())
    vals["GPU"] = "total"

    df_usage_partition = pd.concat([df_usage_partition, pd.DataFrame([vals])])

    df_usage_partition["load"] = (
        df_usage_partition["consumption"] / df_usage_partition["available"]
    )

    return df_usage_partition[["GPU", "load"]]


def print_usage_fraction_per_qos(ddf: pd.DataFrame) -> None:
    ddf = ddf[ddf["GPU"].isna()].copy()
    ddf["consumption"] = ddf["duration"] * ddf["cpus_req"]
    df_usage_partition = (
        ddf.groupby(["id_qos", "partition"])
        .apply(lambda x: sum(x["consumption"]))
        .rename("consumption")
        .reset_index()
    )
    df_usage_partition["users"] = df_usage_partition["id_qos"].apply(
        lambda x: id_qos_name[x]
    )
    df_usage_partition = df_usage_partition.merge(
        df_usage_partition.groupby("partition")
        .apply(lambda x: sum(x["consumption"]))
        .rename("total")
        .reset_index()
    )
    df_usage_partition["fraction"] = (
        df_usage_partition["consumption"] / df_usage_partition["total"]
    )
    print("Usage by QOS")
    print(df_usage_partition[["partition", "users", "fraction"]])
    print("")


def generate_metrics_for_period(start_date: datetime, end_date: datetime):
    df = get_raw_data_for_time_period(start_date, end_date)

    # print_usage_fraction_per_qos(df)
    # For the whole duration
    df_load_cpu_total = get_cpu_load(df, start_date, end_date)
    df_load_gpu_total = get_gpu_load(df, start_date, end_date)

    # Then as a timeseries for each day
    df_list = []
    current_day = start_date
    while current_day < end_date:
        day_start = datetime.combine(current_day, time.min)
        day_end = datetime.combine(current_day, time(23, 59))

        ddf = trim_df_between_dates(df, day_start, day_end)

        df_load_cpu = get_cpu_load(ddf, day_start, day_end)
        df_load_cpu["date"] = current_day
        df_list.append(df_load_cpu)

        df_load_gpu = get_gpu_load(ddf, day_start, day_end)
        df_load_gpu["date"] = current_day
        df_list.append(df_load_gpu)

        current_day += timedelta(days=1)

    df_load_timeseries = pd.concat(df_list)

    df_total_timeseries = df_load_timeseries.query(
        "partition == 'total' or GPU == 'total'"
    )
    df_total_timeseries["Ressource"] = df_total_timeseries.apply(
        lambda x: "GPU" if x["GPU"] == "total" else "CPU", axis=1
    )
    df_total_timeseries.drop(columns=["partition", "GPU"], inplace=True)

    return df_load_cpu_total, df_load_gpu_total, df_total_timeseries
