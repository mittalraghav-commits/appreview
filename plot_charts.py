#!/usr/bin/env python3
import json
import os
from typing import Dict, List

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

TRENDS_PATH = "/workspace/analysis_output/trends.json"
OUT_DIR = "/workspace/analysis_output"


def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def stacked_area_by_week(by_week: Dict[str, Dict[str, int]], week_totals: Dict[str, int], title: str, fname: str) -> None:
    weeks = sorted(int(w) for w in by_week.keys())
    if not weeks:
        return
    categories: List[str] = sorted({c for w in by_week.values() for c in w.keys()})
    data = {c: [] for c in categories}
    for w in weeks:
        wkey = str(w)
        total = max(week_totals.get(wkey, 0), 1)
        for c in categories:
            data[c].append(by_week.get(wkey, {}).get(c, 0) / total)

    fig, ax = plt.subplots(figsize=(10, 6))
    ax.stackplot(weeks, [data[c] for c in categories], labels=categories, alpha=0.85)
    ax.set_title(title)
    ax.set_xlabel("Week")
    ax.set_ylabel("Share of reviews")
    ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1), fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, fname), dpi=160)
    plt.close(fig)


def top_subcategories_bar(by_week_sub: Dict[str, Dict[str, int]], week_totals: Dict[str, int], top_n: int = 10) -> None:
    # Use the latest week for a snapshot
    if not week_totals:
        return
    latest_week = max(int(w) for w in week_totals.keys())
    latest = by_week_sub.get(str(latest_week), {})
    items = sorted(latest.items(), key=lambda x: x[1], reverse=True)[:top_n]
    if not items:
        return
    labels, values = zip(*items)
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.barh(labels, values, color="#4C78A8")
    ax.invert_yaxis()
    ax.set_title(f"Top {top_n} subcategories – Week {latest_week}")
    ax.set_xlabel("Count")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_DIR, f"top_subcategories_week_{latest_week}.png"), dpi=160)
    plt.close(fig)


def main() -> None:
    ensure_dir(OUT_DIR)
    with open(TRENDS_PATH, "r", encoding="utf-8") as f:
        trends = json.load(f)
    stacked_area_by_week(trends["by_week_cat"], trends["week_totals"], "Category share by week", "category_share_by_week.png")
    stacked_area_by_week(trends["by_week_sub"], trends["week_totals"], "Subcategory share by week", "subcategory_share_by_week.png")
    top_subcategories_bar(trends["by_week_sub"], trends["week_totals"], top_n=12)
    print("Charts saved to analysis_output")


if __name__ == "__main__":
    main()

