import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class Theme:
    name: str


THEMES = [
    Theme("Ads related issues"),
    Theme("Coins related issues"),
    Theme("Content discovery issues"),
    Theme("Listening related issues"),
    Theme("Payments & Support"),
    Theme("Localization & Availability"),
    Theme("Content quality & format"),
    Theme("Other")
]


# Canonical subcategory mapping to themes (MECE by design here)
SUBCAT_TO_THEME: Dict[str, str] = {
    # Ads related
    "Ads gating / too many ads": "Ads related issues",
    "Misleading ads / bait-and-switch": "Ads related issues",
    "Story mismatch vs ads": "Ads related issues",

    # Coins related
    "Too expensive / high coin cost": "Coins related issues",
    "Too slow unlock / few free episodes": "Coins related issues",
    "Subscription needed / request": "Coins related issues",

    # Listening related
    "Crashes / app not working": "Listening related issues",
    "Buffering / won't load": "Listening related issues",
    "Playback jumps / episode switching": "Listening related issues",
    "Offline / download issues": "Listening related issues",
    "Notifications / interruptions": "Listening related issues",

    # Payments & Support
    "Billing / refund / trial issues": "Payments & Support",
    "Unauthorized charge / auto pay": "Payments & Support",
    "Support unresponsive": "Payments & Support",

    # Localization
    "Missing languages / dubbing": "Localization & Availability",

    # Content quality & format
    "AI voices / quality": "Content quality & format",
    "Visual vs audio expectation": "Content quality & format",
}


# Fallback: category label to theme
CATEGORY_TO_THEME: Dict[str, str] = {
    "Playback & Performance": "Listening related issues",
    "Monetization & Pricing": "Coins related issues",
    "Payments & Support": "Payments & Support",
    "Localization & Availability": "Localization & Availability",
    # Content & UX maps to content quality & format unless we detect discovery via text
    "Content & UX": "Content quality & format",
}


# Heuristic keyword rules for themes when subcategory is missing/unknown
THEME_REGEXES: List[Tuple[str, re.Pattern]] = [
    ("Ads related issues", re.compile(r"\b(ad|ads|advert|commercial)s?\b", re.IGNORECASE)),
    ("Coins related issues", re.compile(r"\b(coin|price|expensive|cost|paywall|micro\s*transaction|subscription)\b", re.IGNORECASE)),
    ("Listening related issues", re.compile(r"\b(crash|buffer|lag|freeze|bug|download|offline|load(ing)?|not\s+work(ing)?)\b", re.IGNORECASE)),
    ("Payments & Support", re.compile(r"\b(refund|charged?|billing|invoice|payment|customer\s*service|support|help|contact)\b", re.IGNORECASE)),
    ("Localization & Availability", re.compile(r"\b(language|dub|translation|locali[sz]ation|region|available|availability)\b", re.IGNORECASE)),
]


# Heuristic keyword rules for content discovery issues
DISCOVERY_REGEX = re.compile(
    r"(start(s|ed)?\s+another\s+series|auto[- ]?start|recommend|discover|search|find(\s+new)?|home\s+(page|feed)|curat|suggest|no\s+new\s+stor)",
    re.IGNORECASE,
)


# Canonical subcategory mapping for discovery-related issues (MECE within the theme)
DISCOVERY_SUBCATS: List[Tuple[str, re.Pattern]] = [
    ("Auto-starts other series", re.compile(r"start(s|ed)?\s+another\s+series|auto[- ]?start", re.IGNORECASE)),
    ("Poor recommendations/irrelevant suggestions", re.compile(r"recommend|suggest|curat", re.IGNORECASE)),
    ("Search/discoverability issues", re.compile(r"search|find(\s+new)?|home\s+(page|feed)", re.IGNORECASE)),
    ("Lack of new content", re.compile(r"no\s+new\s+stor", re.IGNORECASE)),
]


def _split_multi(value: Optional[str]) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, str):
        value = str(value)
    parts = [p.strip() for p in value.split(";") if p and str(p).strip()]
    return parts


def _infer_discovery_subcategory(text: str) -> Optional[str]:
    for label, pattern in DISCOVERY_SUBCATS:
        if pattern.search(text or ""):
            return label
    return None


def _assign_theme_and_subcat(row: pd.Series) -> List[Tuple[str, str]]:
    assignments: List[Tuple[str, str]] = []

    # Ensure review_text is a string for regex
    rt = row.get("review_text", "")
    review_text = rt if isinstance(rt, str) else ("" if pd.isna(rt) else str(rt))
    categories = _split_multi(row.get("categories"))
    subcategories = _split_multi(row.get("subcategories"))

    # 1) Use explicit subcategories if present
    for subcat in subcategories:
        theme = SUBCAT_TO_THEME.get(subcat)
        if theme:
            assignments.append((theme, subcat))

    # 2) If nothing assigned yet, map categories to themes
    if not assignments:
        for cat in categories:
            theme = CATEGORY_TO_THEME.get(cat)
            if theme:
                # Use category as subcategory placeholder if no subcategory
                assignments.append((theme, cat))

    # 3) Discovery-specific detection from text (only add if not already assigned under discovery)
    if DISCOVERY_REGEX.search(review_text):
        subcat = _infer_discovery_subcategory(review_text) or "Content discovery friction"
        assignments.append(("Content discovery issues", subcat))

    # 4) Heuristic theme detection from text as fallback
    if not assignments:
        for theme_name, pattern in THEME_REGEXES:
            if pattern.search(review_text):
                assignments.append((theme_name, theme_name))
                break

    # 5) If still nothing, bucket as Other
    if not assignments:
        assignments.append(("Other", "Other"))

    # De-duplicate pairs
    deduped = list({(t, s) for t, s in assignments})
    return deduped


def compute_counts_and_trends(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    # Build assignments per row
    df_assign = (
        df.apply(_assign_theme_and_subcat, axis=1)
          .rename("assignments")
          .to_frame()
    )

    # Explode assignments into theme/subcategory columns
    exploded = df_assign.assign(temp=df_assign["assignments"]).explode("temp", ignore_index=True)
    exploded[["theme", "subcategory"]] = pd.DataFrame(exploded["temp"].tolist(), index=exploded.index)
    exploded = exploded.drop(columns=["assignments", "temp"])  # keep only theme/subcategory

    # Join back essential time fields
    exploded = exploded.join(df[["day_index", "week_bucket", "week_label"]])

    # Overall counts
    overall_theme = exploded.groupby("theme", as_index=False).size().rename(columns={"size": "count"}).sort_values("count", ascending=False)
    overall_subcat = (
        exploded.groupby(["theme", "subcategory"], as_index=False).size()
        .rename(columns={"size": "count"})
        .sort_values(["theme", "count"], ascending=[True, False])
    )

    # Daily counts (day_index assumed integer)
    daily_theme = (
        exploded.groupby(["day_index", "theme"], as_index=False).size()
        .rename(columns={"size": "count"})
        .sort_values(["day_index", "theme"]) 
    )

    daily_subcat = (
        exploded.groupby(["day_index", "theme", "subcategory"], as_index=False).size()
        .rename(columns={"size": "count"})
        .sort_values(["day_index", "theme", "count"], ascending=[True, True, False])
    )

    # Compute day-over-day deltas at theme level
    daily_theme["dod_change"] = daily_theme.groupby("theme")["count"].diff()
    daily_theme["dod_change_pct"] = (
        (daily_theme["count"] - daily_theme.groupby("theme")["count"].shift(1))
        / daily_theme.groupby("theme")["count"].shift(1)
    ).replace([np.inf, -np.inf], np.nan)

    # Simple anomaly detection using rolling z-score (window=7)
    daily_theme["rolling_mean_7"] = daily_theme.groupby("theme")["count"].transform(lambda x: x.rolling(window=7, min_periods=3).mean())
    daily_theme["rolling_std_7"] = daily_theme.groupby("theme")["count"].transform(lambda x: x.rolling(window=7, min_periods=3).std(ddof=0))
    daily_theme["zscore_7"] = (daily_theme["count"] - daily_theme["rolling_mean_7"]) / daily_theme["rolling_std_7"]

    anomalies = daily_theme[(daily_theme["zscore_7"] >= 2.0) & daily_theme["rolling_std_7"].notna()].copy()
    anomalies = anomalies.sort_values(["day_index", "zscore_7"], ascending=[True, False])

    return {
        "overall_theme": overall_theme,
        "overall_subcat": overall_subcat,
        "daily_theme": daily_theme,
        "daily_subcat": daily_subcat,
        "anomalies": anomalies,
        "exploded": exploded,
    }


def main() -> None:
    input_path = "/workspace/analysis_output/parsed_reviews.csv"
    out_dir = "/workspace/analysis_output"

    df = pd.read_csv(input_path)

    # Ensure required columns exist
    for col in ["day_index", "categories", "subcategories", "review_text", "week_bucket", "week_label"]:
        if col not in df.columns:
            df[col] = np.nan

    results = compute_counts_and_trends(df)

    # Write outputs
    results["overall_theme"].to_csv(f"{out_dir}/overall_theme_counts.csv", index=False)
    results["overall_subcat"].to_csv(f"{out_dir}/overall_subcategory_counts.csv", index=False)
    results["daily_theme"].to_csv(f"{out_dir}/daily_theme_counts.csv", index=False)
    results["daily_subcat"].to_csv(f"{out_dir}/daily_subcategory_counts.csv", index=False)
    results["anomalies"].to_csv(f"{out_dir}/anomalies_daily_theme.csv", index=False)

    # Print a concise summary
    top_themes = results["overall_theme"].head(10)
    top_subcats = results["overall_subcat"].groupby("theme").head(3)

    print("Top themes (overall):")
    print(top_themes.to_string(index=False))
    print("\nTop subcategories per theme (top 3 each):")
    for theme_name, grp in top_subcats.groupby("theme"):
        print(f"\n[{theme_name}]")
        print(grp[["subcategory", "count"]].to_string(index=False))

    # Recent day-over-day increases (last day vs previous)
    if not results["daily_theme"].empty:
        last_day = int(results["daily_theme"]["day_index"].max())
        recent = results["daily_theme"][results["daily_theme"]["day_index"].isin([last_day - 1, last_day])]
        pivot = recent.pivot_table(index="theme", columns="day_index", values="count", fill_value=0)
        pivot["DoD_change"] = pivot.get(last_day, 0) - pivot.get(last_day - 1, 0)
        pivot = pivot.sort_values("DoD_change", ascending=False)
        print("\nDay-over-day changes (last day vs previous):")
        print(pivot[["DoD_change"]].to_string())

    if not results["anomalies"].empty:
        print("\nDetected anomalies (z>=2) at theme level:")
        print(results["anomalies"][["day_index", "theme", "count", "zscore_7"]].head(20).to_string(index=False))


if __name__ == "__main__":
    main()

