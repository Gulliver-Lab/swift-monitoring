import matplotlib as mpl
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ── Palette (light theme) ──────────────────────────────────────────────────────
BG = "#F7F8FA"
PANEL = "#FFFFFF"
BORDER = "#DDE1E7"
TEXT_PRI = "#1A1D23"
TEXT_SEC = "#6B7280"
ACCENT_CPU = "#2563EB"  # strong blue
ACCENT_GPU = "#16A34A"  # strong green
ACCENT_WARN = "#DC2626"  # red  (total reference line)
WEEKEND_BG = "#E8EDF5"  # muted blue-grey for weekend columns
WEEKEND_LN = "#B0BDD6"  # weekend column border
GRID_COLOR = "#E5E7EB"

mpl.rcParams.update(
    {
        "font.family": "monospace",
        "text.color": TEXT_PRI,
        "axes.facecolor": PANEL,
        "axes.edgecolor": BORDER,
        "axes.labelcolor": TEXT_SEC,
        "axes.titlecolor": TEXT_PRI,
        "xtick.color": TEXT_SEC,
        "ytick.color": TEXT_SEC,
        "grid.color": GRID_COLOR,
        "grid.linewidth": 0.7,
        "figure.facecolor": BG,
        "savefig.facecolor": BG,
    }
)


def pct(v: float) -> str:
    return f"{v * 100:.1f}%"


def draw_gauge(ax, value: float, color: str, label: str):
    """Half-donut gauge."""
    angles_bg = np.linspace(0, np.pi, 300)
    ax.plot(
        np.cos(angles_bg),
        np.sin(angles_bg),
        lw=20,
        color=BORDER,
        solid_capstyle="round",
        zorder=1,
    )
    if value > 0:
        angles_v = np.linspace(0, np.pi * value, max(2, int(300 * value)))
        ax.plot(
            np.cos(angles_v),
            np.sin(angles_v),
            lw=20,
            color=color,
            solid_capstyle="round",
            zorder=2,
        )

    ax.text(
        0,
        0.22,
        pct(value),
        ha="center",
        va="center",
        fontsize=19,
        fontweight="bold",
        color=TEXT_PRI,
    )
    ax.text(0, -0.08, label, ha="center", va="center", fontsize=8, color=TEXT_SEC)

    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-0.30, 1.20)
    ax.set_aspect("equal")
    ax.axis("off")


def draw_hbar(ax, names, values, total_val, color: str, title: str):
    """Horizontal bar chart."""
    n = len(names)
    y = np.arange(n)
    pct_vals = [v * 100 for v in values]

    # alternating row backgrounds
    for i in range(n):
        ax.axhspan(i - 0.45, i + 0.45, color=BG, zorder=0)

    bars = ax.barh(
        y, pct_vals, height=0.52, color=color, alpha=0.80, linewidth=0, zorder=2
    )

    # total reference line
    ax.axvline(
        total_val * 100, color=ACCENT_WARN, lw=1.4, linestyle="--", alpha=0.9, zorder=5
    )

    # value labels
    for bar, val in zip(bars, values):
        ax.text(
            bar.get_width() + 0.9,
            bar.get_y() + bar.get_height() / 2,
            pct(val),
            va="center",
            ha="left",
            fontsize=8.5,
            color=TEXT_PRI,
            fontweight="bold",
        )

    ax.set_yticks(y)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel("Average load", fontsize=8, labelpad=5)
    ax.set_xlim(0, 112)
    ax.xaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda x, _: f"{x:.0f}%"))
    ax.set_title(
        title, fontsize=10, fontweight="bold", pad=8, loc="left", color=TEXT_PRI
    )
    ax.grid(axis="x", visible=True, zorder=1)
    ax.tick_params(axis="both", length=0)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)

    avg_patch = mpatches.Patch(color=ACCENT_WARN, label=f"Total avg: {pct(total_val)}")
    ax.legend(
        handles=[avg_patch],
        fontsize=7.5,
        loc="lower right",
        framealpha=0.8,
        facecolor=PANEL,
        edgecolor=BORDER,
    )


def draw_bar_ts(ax, ts: pd.DataFrame):
    """
    Grouped bar chart: one CPU bar + one GPU bar per day, side by side.
    Weekend days get a clearly shaded background column.
    """
    cpu = ts[ts["Ressource"] == "CPU"].set_index("date")["load"]
    gpu = ts[ts["Ressource"] == "GPU"].set_index("date")["load"]

    idx = sorted(set(cpu.index) | set(gpu.index))
    cpu = cpu.reindex(idx)
    gpu = gpu.reindex(idx)
    xdates = pd.to_datetime(idx)
    x = np.arange(len(xdates))
    w = 0.38  # width of each bar

    # ── Weekend shading (behind bars) ─────────────────────────────────────────
    for i, d in enumerate(xdates):
        if d.weekday() >= 5:
            ax.axvspan(i - 0.5, i + 0.5, color=WEEKEND_BG, zorder=0, linewidth=0)
            for xv in [i - 0.5, i + 0.5]:
                ax.axvline(
                    xv, color=WEEKEND_LN, lw=0.9, linestyle="-", zorder=1, alpha=0.8
                )

    ax.grid(axis="y", visible=True, zorder=2)

    # ── CPU bars ───────────────────────────────────────────────────────────────
    ax.bar(
        x - w / 2,
        cpu.fillna(0) * 100,
        width=w,
        color=ACCENT_CPU,
        alpha=0.80,
        linewidth=0,
        zorder=3,
        label="CPU",
    )

    # ── GPU bars ───────────────────────────────────────────────────────────────
    ax.bar(
        x + w / 2,
        gpu.fillna(0) * 100,
        width=w,
        color=ACCENT_GPU,
        alpha=0.80,
        linewidth=0,
        zorder=3,
        label="GPU",
    )

    # ── Axes formatting ────────────────────────────────────────────────────────
    ax.set_xlim(-0.7, len(x) - 0.3)
    ax.set_ylim(0, 108)
    ax.set_xticks(x)
    ax.set_xticklabels(
        [d.strftime("%b %d") for d in xdates], rotation=35, ha="right", fontsize=7.5
    )
    ax.yaxis.set_major_formatter(mpl.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))
    ax.set_ylabel("Load (%)", fontsize=8, labelpad=5)
    ax.set_title(
        "Daily average load",
        fontsize=10,
        fontweight="bold",
        pad=8,
        loc="left",
        color=TEXT_PRI,
    )
    ax.tick_params(axis="both", length=0)
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)

    we_patch = mpatches.Patch(color=WEEKEND_BG, edgecolor=WEEKEND_LN, label="Weekend")
    ax.legend(
        fontsize=8,
        framealpha=0.85,
        facecolor=PANEL,
        edgecolor=BORDER,
        loc="upper left",
        handles=[
            mpatches.Patch(color=ACCENT_CPU, label="CPU"),
            mpatches.Patch(color=ACCENT_GPU, label="GPU"),
            we_patch,
        ],
    )


def build_report(
    cpu_df: pd.DataFrame,
    gpu_df: pd.DataFrame,
    ts_df: pd.DataFrame,
    output_path: str,
):

    title = "Cluster Usage Report"

    start_date = ts_df["date"].min()
    end_date = ts_df["date"].max()
    period = start_date.strftime("%B %d %Y") + " - " + end_date.strftime("%B %d %Y")

    cpu_total = float(cpu_df[cpu_df["partition"] == "total"]["load"].iloc[0])
    gpu_total = float(gpu_df[gpu_df["GPU"] == "total"]["load"].iloc[0])
    cpu_parts = cpu_df[cpu_df["partition"] != "total"]
    gpu_types = gpu_df[gpu_df["GPU"] != "total"]

    fig = plt.figure(figsize=(13, 9.5))
    fig.patch.set_facecolor(BG)

    # ── Header ────────────────────────────────────────────────────────────────
    hax = fig.add_axes([0, 0.915, 1, 0.085])  # type: ignore
    hax.set_facecolor(PANEL)
    hax.axis("off")
    hax.add_patch(
        mpl.patches.Rectangle(
            (0, 0),
            0.004,
            1,
            transform=hax.transAxes,
            color=ACCENT_CPU,
            zorder=10,
            clip_on=False,
        )
    )
    hax.text(
        0.014,
        0.62,
        title,
        transform=hax.transAxes,
        fontsize=17,
        fontweight="bold",
        color=TEXT_PRI,
        va="center",
    )
    hax.text(
        0.014,
        0.20,
        period,
        transform=hax.transAxes,
        fontsize=9.5,
        color=TEXT_SEC,
        va="center",
    )
    hax.text(
        0.993,
        0.5,
        "Swift",
        transform=hax.transAxes,
        fontsize=8.5,
        color=TEXT_SEC,
        va="center",
        ha="right",
        alpha=0.55,
    )

    sep = fig.add_axes([0, 0.910, 1, 0.0045])  # type: ignore
    sep.set_facecolor(ACCENT_CPU)
    sep.axis("off")

    # ── Outer grid: top row (gauges+bars) + bottom row (lollipop) ────────────
    outer = gridspec.GridSpec(
        2,
        1,
        figure=fig,
        left=0.06,
        right=0.97,
        top=0.90,
        bottom=0.06,
        hspace=0.50,
        height_ratios=[1, 1.15],
    )

    # Top row split evenly: CPU half | GPU half
    top_gs = gridspec.GridSpecFromSubplotSpec(1, 2, subplot_spec=outer[0], wspace=0.12)

    # Each half: gauge (1) | bar chart (1.8)
    cpu_gs = gridspec.GridSpecFromSubplotSpec(
        1, 2, subplot_spec=top_gs[0], wspace=0.38, width_ratios=[1, 1.4]
    )
    gpu_gs = gridspec.GridSpecFromSubplotSpec(
        1, 2, subplot_spec=top_gs[1], wspace=0.38, width_ratios=[1, 1.4]
    )

    # ── Subplots ──────────────────────────────────────────────────────────────
    gauge_cpu_ax = fig.add_subplot(cpu_gs[0])
    cpu_bar_ax = fig.add_subplot(cpu_gs[1])
    gauge_gpu_ax = fig.add_subplot(gpu_gs[0])
    gpu_bar_ax = fig.add_subplot(gpu_gs[1])
    ts_ax = fig.add_subplot(outer[1])

    draw_gauge(gauge_cpu_ax, cpu_total, ACCENT_CPU, "Avg CPU load")
    draw_gauge(gauge_gpu_ax, gpu_total, ACCENT_GPU, "Avg GPU load")

    draw_hbar(
        cpu_bar_ax,
        cpu_parts["partition"].tolist(),
        cpu_parts["load"].tolist(),
        cpu_total,
        ACCENT_CPU,
        "CPU — per partition",
    )

    draw_hbar(
        gpu_bar_ax,
        gpu_types["GPU"].tolist(),
        gpu_types["load"].tolist(),
        gpu_total,
        ACCENT_GPU,
        "GPU — per device type",
    )

    draw_bar_ts(ts_ax, ts_df)

    # ── Centre divider between CPU and GPU halves ─────────────────────────────
    top_pos = outer[0].get_position(fig)
    line_x = 0.515
    line_ybot = top_pos.y0 + 0.005
    line_ytop = top_pos.y1 - 0.005
    fig.add_artist(
        mpl.lines.Line2D(
            [line_x, line_x],
            [line_ybot, line_ytop],
            transform=fig.transFigure,
            color=BORDER,
            lw=1.2,
            linestyle="--",
            alpha=0.9,
        )
    )

    ## ── Footer ────────────────────────────────────────────────────────────────
    # fig.text(
    #    0.5,
    #    0.012,
    #    f"Generated from Slurm accounting data  \u00b7  {period}",
    #    ha="center",
    #    fontsize=7.5,
    #    color=TEXT_SEC,
    #    alpha=0.55,
    # )

    plt.savefig(output_path, bbox_inches="tight", dpi=180)
    plt.close(fig)
    print(f"Report saved -> {output_path}")
