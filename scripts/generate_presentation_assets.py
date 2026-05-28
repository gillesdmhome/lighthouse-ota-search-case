#!/usr/bin/env python3
"""Generate presentation images, charts, and diagrams for the Lighthouse case deck."""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "presentation" / "assets"
ASSETS.mkdir(parents=True, exist_ok=True)

# Lighthouse-inspired palette
BLUE = "#4A90D9"
BLUE_LIGHT = "#A8CCE8"
RED = "#E57373"
RED_LIGHT = "#F5B7B1"
GREY = "#6B7280"
GREY_LIGHT = "#E5E7EB"
GREEN = "#34A853"
DARK = "#1F2937"
BG = "#FAFBFC"


def _save(fig, name: str) -> None:
    path = ASSETS / name
    fig.savefig(path, dpi=180, bbox_inches="tight", facecolor=BG, edgecolor="none")
    plt.close(fig)
    print(f"  saved {path.name}")


def chart_arrival_date_popularity() -> None:
    """Search level time-series (matches case mockup style)."""
    dates = ["Jan 24", "Jan 31", "Feb 7", "Feb 14", "Feb 21", "Feb 28", "Mar 7", "Mar 14", "Mar 21"]
    values = [120, 95, 180, 210, 165, 140, 110, 85, 70]
    colors = [BLUE if v < 170 else RED for v in values]

    fig, ax = plt.subplots(figsize=(10, 4))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor("white")
    ax.bar(dates, values, color=colors, width=0.65, edgecolor="white", linewidth=0.8)
    ax.set_title("Search Level — Arrival Date Popularity (New York)", fontsize=14, fontweight="bold", color=DARK, pad=12)
    ax.set_ylabel("Search count", fontsize=10, color=GREY)
    ax.tick_params(axis="x", rotation=45, labelsize=9)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)
    _save(fig, "03_arrival_date_popularity.png")


def chart_country_trends() -> None:
    """Top countries searching with % share and avg LOS."""
    countries = ["United States", "Switzerland", "Germany", "Brazil", "United Kingdom"]
    pcts = [23.4, 17.2, 14.3, 9.3, 7.4]
    avg_los = [5.5, 3.6, 4.0, 6.4, 5.2]

    fig, ax = plt.subplots(figsize=(8, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor("white")
    y_pos = range(len(countries))
    bars = ax.barh(y_pos, pcts, color=BLUE, height=0.55, edgecolor="white")
    ax.set_yticks(y_pos)
    ax.set_yticklabels(countries, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlabel("% of total searches", fontsize=10, color=GREY)
    ax.set_title("Top Countries Searching", fontsize=14, fontweight="bold", color=DARK, pad=12)
    for i, (bar, pct, los) in enumerate(zip(bars, pcts, avg_los)):
        ax.text(bar.get_width() + 0.5, bar.get_y() + bar.get_height() / 2,
                f"{pct}%  ·  Avg LOS: {los}", va="center", fontsize=9, color=DARK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, 30)
    _save(fig, "04_country_trends.png")


def chart_los_distribution() -> None:
    """Length-of-stay distribution buckets."""
    buckets = ["LOS1\n(1 night)", "LOS2\n(2 nights)", "LOS3\n(3 nights)", "LOS4-7\n(4-7 nights)", "LOS8-14\n(8-14 nights)"]
    pcts = [41.5, 23.9, 13.7, 17.4, 3.6]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor("white")
    bars = ax.barh(buckets, pcts, color=[BLUE, BLUE_LIGHT, BLUE_LIGHT, RED_LIGHT, RED], height=0.6)
    ax.invert_yaxis()
    ax.set_xlabel("% of searches", fontsize=10, color=GREY)
    ax.set_title("Length-of-Stay Distribution", fontsize=14, fontweight="bold", color=DARK, pad=12)
    for bar, pct in zip(bars, pcts):
        ax.text(bar.get_width() + 0.8, bar.get_y() + bar.get_height() / 2,
                f"{pct}%", va="center", fontsize=10, fontweight="bold", color=DARK)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_xlim(0, 50)
    _save(fig, "05_los_distribution.png")


def chart_market_insight_dashboard() -> None:
    """Composite dashboard matching the case PDF mockup."""
    fig = plt.figure(figsize=(14, 8))
    fig.patch.set_facecolor(BG)
    fig.suptitle("Market Insight — Searches in the last 7 days (New York)", fontsize=16, fontweight="bold", color=DARK, y=0.98)

    # Arrival date chart
    ax1 = fig.add_subplot(2, 2, (1, 2))
    dates = ["Jan 24", "Jan 31", "Feb 7", "Feb 14", "Feb 21", "Feb 28", "Mar 7", "Mar 14", "Mar 21"]
    values = [120, 95, 180, 210, 165, 140, 110, 85, 70]
    colors = [BLUE if v < 170 else RED for v in values]
    ax1.bar(dates, values, color=colors, width=0.65)
    ax1.set_title("Search Level", fontsize=12, fontweight="bold", loc="left")
    ax1.tick_params(axis="x", rotation=45, labelsize=8)
    ax1.grid(axis="y", alpha=0.3, linestyle="--")
    ax1.spines[["top", "right"]].set_visible(False)

    # Countries
    ax2 = fig.add_subplot(2, 2, 3)
    countries = ["United States", "Switzerland", "Germany", "Brazil", "UK"]
    pcts = [23.4, 17.2, 14.3, 9.3, 7.4]
    ax2.barh(countries, pcts, color=BLUE, height=0.55)
    ax2.invert_yaxis()
    ax2.set_title("Top Countries Searching", fontsize=12, fontweight="bold", loc="left")
    ax2.spines[["top", "right"]].set_visible(False)

    # LOS
    ax3 = fig.add_subplot(2, 2, 4)
    buckets = ["LOS1", "LOS2", "LOS3", "LOS4-7", "LOS8-14"]
    los_pcts = [41.5, 23.9, 13.7, 17.4, 3.6]
    ax3.barh(buckets, los_pcts, color=[BLUE, BLUE_LIGHT, BLUE_LIGHT, RED_LIGHT, RED], height=0.55)
    ax3.invert_yaxis()
    ax3.set_title("Length-of-Stay", fontsize=12, fontweight="bold", loc="left")
    ax3.spines[["top", "right"]].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    _save(fig, "02_market_insight_dashboard.png")


def diagram_architecture_overview() -> None:
    """End-to-end pipeline architecture."""
    fig, ax = plt.subplots(figsize=(14, 5))
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.set_title("OTA Search Ingestion Pipeline — Architecture Overview", fontsize=14, fontweight="bold", color=DARK, pad=16)

    boxes = [
        (0.3, 2.2, "OTA\nPartner", "#FFF3E0", "#E65100"),
        (1.8, 2.2, "Cloud Load\nBalancer", GREY_LIGHT, GREY),
        (3.3, 2.2, "FastAPI\nCloud Run", "#E3F2FD", BLUE),
        (4.8, 2.2, "Pub/Sub", "#E8F5E9", GREEN),
        (6.3, 2.2, "Dataflow\nBeam Python", "#E3F2FD", BLUE),
        (7.8, 2.2, "BigQuery\nBronze + GCS", "#FFF8E1", "#F9A825"),
        (9.3, 2.2, "Airflow\n+ dbt", "#F3E5F5", "#7B1FA2"),
        (10.8, 2.2, "BigQuery\nSilver / Gold", "#FFF8E1", "#F9A825"),
        (12.3, 2.2, "Market Insight\nGKE", "#E8F5E9", GREEN),
    ]
    for x, y, label, fc, ec in boxes:
        box = FancyBboxPatch((x, y), 1.2, 1.0, boxstyle="round,pad=0.05", facecolor=fc, edgecolor=ec, linewidth=1.5)
        ax.add_patch(box)
        ax.text(x + 0.6, y + 0.5, label, ha="center", va="center", fontsize=8, fontweight="bold", color=DARK)

    for x in [1.5, 3.0, 4.5, 6.0, 7.5, 9.0, 10.5, 12.0]:
        ax.annotate("", xy=(x + 0.25, 2.7), xytext=(x, 2.7),
                    arrowprops=dict(arrowstyle="->", color=GREY, lw=1.5))

    # DLQ branch
    box = FancyBboxPatch((4.8, 0.5), 1.2, 0.7, boxstyle="round,pad=0.05", facecolor="#FFEBEE", edgecolor=RED, linewidth=1.5)
    ax.add_patch(box)
    ax.text(5.4, 0.85, "DLQ", ha="center", va="center", fontsize=8, fontweight="bold", color=RED)
    ax.annotate("", xy=(5.4, 1.2), xytext=(5.4, 2.2), arrowprops=dict(arrowstyle="->", color=RED, lw=1.2, linestyle="dashed"))

    _save(fig, "01_architecture_overview.png")


def diagram_medallion() -> None:
    """Bronze / silver / gold medallion layers."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("Medallion Data Model (BigQuery)", fontsize=14, fontweight="bold", color=DARK, pad=16)

    layers = [
        (1, 4, "BRONZE", "raw_ota_searches", "Full JSON · append-only · 90-day TTL\nPartitioned by ingestion_time", "#CD7F32"),
        (1, 2.2, "SILVER", "searches_enriched", "Typed · city resolved · deduped\nIncremental dbt merge on dedup_key", "#C0C0C0"),
        (1, 0.4, "GOLD", "3 trend tables", "Pre-aggregated for Market Insight\n~5 GB total (not 260 GB bronze)", "#FFD700"),
    ]
    for x, y, tier, table, desc, color in layers:
        box = FancyBboxPatch((x, y), 8, 1.5, boxstyle="round,pad=0.08", facecolor="white", edgecolor=color, linewidth=2.5)
        ax.add_patch(box)
        ax.text(x + 0.3, y + 1.05, tier, fontsize=11, fontweight="bold", color=color)
        ax.text(x + 2.2, y + 1.05, table, fontsize=11, fontweight="bold", color=DARK)
        ax.text(x + 0.3, y + 0.35, desc, fontsize=9, color=GREY)

    for y in [3.7, 1.9]:
        ax.annotate("", xy=(5, y), xytext=(5, y + 0.5), arrowprops=dict(arrowstyle="->", color=GREY, lw=2))

    _save(fig, "06_medallion_layers.png")


def diagram_validation_layers() -> None:
    """Three-layer validation strategy."""
    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    ax.set_title("Data Validation — Three Layers", fontsize=14, fontweight="bold", color=DARK, pad=16)

    layers = [
        (0.5, 4.2, "Layer 1 — Edge (sync)", "JSON Schema + Python validator", "< 10 ms · 400 on failure", BLUE),
        (0.5, 2.4, "Layer 2 — Warehouse", "dbt tests + singular SQL checks", "After each dbt run · block gold", "#7B1FA2"),
        (0.5, 0.6, "Layer 3 — Monitoring", "Soda Core scans", "Anomaly detection · alert team", GREEN),
    ]
    for x, y, title, tool, detail, color in layers:
        box = FancyBboxPatch((x, y), 9, 1.4, boxstyle="round,pad=0.06", facecolor="white", edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x + 0.3, y + 0.95, title, fontsize=11, fontweight="bold", color=color)
        ax.text(x + 0.3, y + 0.55, tool, fontsize=10, color=DARK)
        ax.text(x + 0.3, y + 0.2, detail, fontsize=9, color=GREY, style="italic")

    ax.annotate("", xy=(5, 4.0), xytext=(5, 3.9), arrowprops=dict(arrowstyle="->", color=GREY, lw=1.5))
    ax.annotate("", xy=(5, 2.2), xytext=(5, 2.1), arrowprops=dict(arrowstyle="->", color=GREY, lw=1.5))

    _save(fig, "07_validation_layers.png")


def chart_cost_breakdown() -> None:
    """Monthly cost breakdown bar chart."""
    components = ["Composer", "Dataflow", "BigQuery", "Cloud Run\n+ LB", "Pub/Sub\n+ GCS", "Monitoring", "Other"]
    low = [300, 150, 55, 50, 10, 20, 5]
    high = [500, 400, 220, 120, 25, 50, 15]

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor("white")
    x = range(len(components))
    ax.bar(x, high, color=BLUE_LIGHT, label="High estimate", width=0.5, alpha=0.6)
    ax.bar(x, low, color=BLUE, label="Low estimate", width=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(components, fontsize=9)
    ax.set_ylabel("USD / month", fontsize=10, color=GREY)
    ax.set_title("Monthly Infrastructure Cost (Production, EU)", fontsize=14, fontweight="bold", color=DARK, pad=12)
    ax.legend(fontsize=9)
    ax.axhline(y=650, color=GREEN, linestyle="--", alpha=0.7, label="MVP ceiling")
    ax.axhline(y=1500, color=RED, linestyle="--", alpha=0.7, label="Prod ceiling")
    ax.text(len(components) - 0.5, 670, "Low ~$650", fontsize=8, color=GREEN)
    ax.text(len(components) - 0.5, 1520, "High ~$1,500", fontsize=8, color=RED)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    _save(fig, "08_cost_breakdown.png")


def chart_mvp_phasing() -> None:
    """MVP phasing timeline."""
    phases = ["Phase 1\nMVP", "Phase 2\nStreaming", "Phase 3\nProduction"]
    costs = [300, 700, 1100]
    weeks = [3, 5, 8]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.patch.set_facecolor(BG)
    fig.suptitle("MVP Phasing — Cost & Timeline", fontsize=14, fontweight="bold", color=DARK)

    colors = [GREEN, BLUE, "#7B1FA2"]
    ax1.bar(phases, costs, color=colors, width=0.55, edgecolor="white")
    ax1.set_ylabel("Est. monthly cost (USD)", fontsize=10)
    ax1.set_title("Cost by phase", fontsize=11, fontweight="bold")
    for i, c in enumerate(costs):
        ax1.text(i, c + 30, f"~${c}/mo", ha="center", fontsize=10, fontweight="bold")
    ax1.spines[["top", "right"]].set_visible(False)

    ax2.bar(phases, weeks, color=colors, width=0.55, edgecolor="white")
    ax2.set_ylabel("Cumulative weeks", fontsize=10)
    ax2.set_title("Timeline", fontsize=11, fontweight="bold")
    for i, w in enumerate(weeks):
        ax2.text(i, w + 0.2, f"Week {w}", ha="center", fontsize=10, fontweight="bold")
    ax2.spines[["top", "right"]].set_visible(False)

    plt.tight_layout()
    _save(fig, "09_mvp_phasing.png")


def diagram_lambda_layers() -> None:
    """Speed / batch / serving layers."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    ax.axis("off")
    ax.set_title("Lambda-Inspired Layering", fontsize=14, fontweight="bold", color=DARK, pad=16)

    layers = [
        (0.5, 3.2, "Speed Layer", "Dataflow → Bronze", "Seconds", BLUE),
        (0.5, 1.7, "Batch Layer", "Airflow + dbt → Silver/Gold", "15 minutes", "#7B1FA2"),
        (0.5, 0.2, "Serving Layer", "Market Insight GKE", "Pre-aggregated reads", GREEN),
    ]
    for x, y, name, comp, lat, color in layers:
        box = FancyBboxPatch((x, y), 9, 1.2, boxstyle="round,pad=0.06", facecolor="white", edgecolor=color, linewidth=2)
        ax.add_patch(box)
        ax.text(x + 0.3, y + 0.75, name, fontsize=11, fontweight="bold", color=color)
        ax.text(x + 3.0, y + 0.75, comp, fontsize=10, color=DARK)
        ax.text(x + 7.5, y + 0.75, lat, fontsize=10, fontweight="bold", color=GREY, ha="right")

    _save(fig, "10_lambda_layers.png")


def chart_throughput_volume() -> None:
    """Throughput and volume infographic."""
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.5))
    fig.patch.set_facecolor(BG)
    fig.suptitle("Pipeline Volume at 100 req/s", fontsize=14, fontweight="bold", color=DARK)

    metrics = [
        ("100", "requests/sec"),
        ("8.6M", "events/day"),
        ("260 GB", "raw/month"),
    ]
    for ax, (val, label) in zip(axes, metrics):
        ax.set_facecolor("white")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        circle = plt.Circle((0.5, 0.55), 0.35, color=BLUE_LIGHT, alpha=0.5)
        ax.add_patch(circle)
        ax.text(0.5, 0.6, val, ha="center", va="center", fontsize=22, fontweight="bold", color=BLUE)
        ax.text(0.5, 0.15, label, ha="center", va="center", fontsize=11, color=GREY)

    plt.tight_layout()
    _save(fig, "11_throughput_volume.png")


def image_sample_json() -> None:
    """Sample JSON payload from case PDF."""
    payload = textwrap.dedent("""\
    {
      "arrival_date": "2022-03-01",
      "departure_date": "2022-03-05",
      "length_of_stay": 4,
      "user_country": "Belgium",
      "hotel_id": 1235,
      "hotel_name": "Holiday Inn Manhattan",
      "hotel_latitude": 40.70825421355257,
      "hotel_longitude": -74.0142071188057,
      "timestamp": "2022-01-24T11:01:12",
      "search_results": [
        { "room_name": "Deluxe Suite", "price": 124, "currency": "USD" }
      ]
    }""")

    fig, ax = plt.subplots(figsize=(9, 6))
    fig.patch.set_facecolor(BG)
    ax.axis("off")
    ax.set_title("Inbound OTA Search Event (JSON Schema v1)", fontsize=13, fontweight="bold", color=DARK, pad=12)
    box = FancyBboxPatch((0.05, 0.05), 0.9, 0.85, boxstyle="round,pad=0.02", facecolor="#1E1E1E", edgecolor=GREY, linewidth=1)
    ax.add_patch(box)
    ax.text(0.08, 0.82, payload, fontsize=9, color="#D4D4D4", family="monospace", va="top",
            transform=ax.transAxes)
    _save(fig, "12_sample_json_payload.png")


def diagram_orchestration_dag() -> None:
    """Airflow DAG task flow."""
    fig, ax = plt.subplots(figsize=(12, 3))
    fig.patch.set_facecolor(BG)
    ax.set_xlim(0, 12)
    ax.set_ylim(0, 3)
    ax.axis("off")
    ax.set_title("Airflow DAG — ota_search_pipeline (every 15 min)", fontsize=13, fontweight="bold", color=DARK, pad=14)

    tasks = [
        "Check\nDataflow", "dbt\nSilver", "dbt\nGold", "dbt\nTest", "Soda\nScan", "Expire\nPartitions"
    ]
    for i, task in enumerate(tasks):
        x = 0.5 + i * 1.9
        box = FancyBboxPatch((x, 1.0), 1.5, 1.0, boxstyle="round,pad=0.05", facecolor="#F3E5F5", edgecolor="#7B1FA2", linewidth=1.5)
        ax.add_patch(box)
        ax.text(x + 0.75, 1.5, task, ha="center", va="center", fontsize=8, fontweight="bold", color=DARK)
        if i < len(tasks) - 1:
            ax.annotate("", xy=(x + 1.6, 1.5), xytext=(x + 1.5, 1.5),
                        arrowprops=dict(arrowstyle="->", color=GREY, lw=1.5))

    _save(fig, "13_orchestration_dag.png")


def main() -> None:
    print(f"Generating presentation assets -> {ASSETS}")
    chart_arrival_date_popularity()
    chart_country_trends()
    chart_los_distribution()
    chart_market_insight_dashboard()
    diagram_architecture_overview()
    diagram_medallion()
    diagram_validation_layers()
    chart_cost_breakdown()
    chart_mvp_phasing()
    diagram_lambda_layers()
    chart_throughput_volume()
    image_sample_json()
    diagram_orchestration_dag()
    print(f"Done — {len(list(ASSETS.glob('*.png')))} images in presentation/assets/")


if __name__ == "__main__":
    main()
