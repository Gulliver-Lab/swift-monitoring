from datetime import datetime, time, timedelta

import pandas as pd

from reports.data import get_raw_data_for_time_period
from reports.settings import (
    cpus_per_partition,
    gpu_per_node,
    gpus_per_partition,
    id_qos_name,
    ram_per_partition_mb,
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


def get_available_mem_for_period(
    start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    seconds_for_this_period = (end_date - start_date).total_seconds()
    df_mem = (
        pd.DataFrame([ram_per_partition_mb])
        .T.reset_index()
        .rename(columns={0: "MEM", "index": "partition"})
    )
    df_mem["available"] = df_mem["MEM"] * seconds_for_this_period
    return df_mem[["partition", "available"]]


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


def get_available_gpu_partition_for_period(
    start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    seconds_for_this_period = (end_date - start_date).total_seconds()
    df_gpu = pd.DataFrame(
        [
            {"partition": partition, "GPU": gpu}
            for partition, gpus in gpus_per_partition.items()
            for gpu in gpus
        ]
    )
    if df_gpu.empty:
        return pd.DataFrame(columns=["partition", "GPU", "available"])

    df_gpu = df_gpu.value_counts(["partition", "GPU"]).rename("count").reset_index()
    df_gpu["available"] = df_gpu["count"] * seconds_for_this_period
    return df_gpu[["partition", "GPU", "available"]]


def map_gpu_load_to_partitions(
    df_gpu_load: pd.DataFrame, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    df_gpu_available = get_available_gpu_partition_for_period(start_date, end_date)
    if df_gpu_available.empty:
        return pd.DataFrame(columns=["partition", "load"])

    if "GPU" not in df_gpu_load.columns:
        df_gpu_load = pd.DataFrame(columns=["GPU", "load"])

    df_gpu_load = df_gpu_load[df_gpu_load["GPU"] != "total"]
    df_gpu_partition = (
        df_gpu_available.merge(df_gpu_load, how="left", on="GPU")
        .fillna({"load": 0})
        .assign(consumption=lambda x: x["available"] * x["load"])
    )
    df_gpu_partition = (
        df_gpu_partition.groupby("partition")
        .agg({"consumption": "sum", "available": "sum"})
        .reset_index()
    )
    df_gpu_partition["load"] = (
        df_gpu_partition["consumption"] / df_gpu_partition["available"]
    )
    return df_gpu_partition[["partition", "load"]]


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


def get_mem_load(
    ddf: pd.DataFrame, start_date: datetime, end_date: datetime
) -> pd.DataFrame:
    ddf = ddf.copy()
    if ddf.empty:
        return pd.DataFrame()

    ddf["required_mem"] = ddf["tres_req"].apply(
        lambda x: float(x.split(",")[1].split("=")[1])
    )
    ddf["consumption"] = ddf["duration"] * ddf["required_mem"]
    df_usage_partition = (
        ddf.groupby(["partition"])
        .apply(lambda x: sum(x["consumption"]))
        .rename("consumption")
        .reset_index()
        .merge(get_available_mem_for_period(start_date, end_date), how="right")
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
    df_load_mem_total = get_mem_load(df, start_date, end_date)
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
        df_load_cpu["Ressource"] = "CPU"
        df_list.append(df_load_cpu)

        df_load_mem = get_mem_load(ddf, day_start, day_end)
        df_load_mem["date"] = current_day
        df_load_mem["Ressource"] = "RAM"
        df_list.append(df_load_mem)

        df_load_gpu = get_gpu_load(ddf, day_start, day_end)
        df_load_gpu["date"] = current_day
        df_load_gpu["Ressource"] = "GPU"
        df_list.append(df_load_gpu)

        df_load_gpu_partition = map_gpu_load_to_partitions(
            df_load_gpu, day_start, day_end
        )
        df_load_gpu_partition["date"] = current_day
        df_load_gpu_partition["Ressource"] = "GPU"
        df_list.append(df_load_gpu_partition)

        current_day += timedelta(days=1)

    df_load_timeseries = pd.concat(df_list)
    df_partition_timeseries = df_load_timeseries[
        (df_load_timeseries["partition"].notna())
        & (df_load_timeseries["partition"] != "total")
    ]
    df_partition_timeseries = df_partition_timeseries.drop(columns=["GPU"])

    return (
        df_load_cpu_total,
        df_load_mem_total,
        df_load_gpu_total,
        df_partition_timeseries,
    )
