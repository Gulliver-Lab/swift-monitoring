import argparse
from datetime import datetime, time

from reports import metrics, plots

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate Slurm usage report PDF")
    parser.add_argument("--output", default="slurm_report.pdf")
    parser.add_argument("--start", required=True)
    parser.add_argument("--end", required=True)
    args = parser.parse_args()

    # Date range for the query
    start_date = datetime.strptime(args.start, "%Y-%m-%d")
    end_date = datetime.strptime(args.end, "%Y-%m-%d")

    # Set the end of the day for this one
    end_date = datetime.combine(end_date, time(23, 59))

    cpu_df, _, gpu_df, ts_df = metrics.generate_metrics_for_period(start_date, end_date)

    plots.build_report(cpu_df, gpu_df, ts_df, args.output)
