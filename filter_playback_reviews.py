#!/usr/bin/env python3
import csv
import json
import os
import re
from typing import Dict, List


INPUT_CSV = "/workspace/analysis_output/parsed_reviews.csv"
OUT_DIR = "/workspace/analysis_output"
OUT_JSON = os.path.join(OUT_DIR, "playback_performance_reviews.json")
OUT_CSV = os.path.join(OUT_DIR, "playback_performance_reviews.csv")


def normalize(text: str) -> str:
    if text is None:
        return ""
    return " ".join(text.strip().split())


def is_playback_or_performance(categories: str, subcategories: str, review_text: str) -> bool:
    categories_l = (categories or "").lower()
    subcategories_l = (subcategories or "").lower()
    text_l = (review_text or "").lower()

    # Category-based inclusion
    if "playback & performance" in categories_l:
        return True

    # Subcategory hints commonly tied to playback/performance
    subcat_terms = [
        "crashes / app not working",
        "buffering / won't load",
        "offline / download issues",
        "playback jumps / episode switching",
    ]
    if any(term in subcategories_l for term in subcat_terms):
        return True

    # Text-based semantic heuristics
    # Keep these reasonably specific to avoid monetization/ads false-positives
    patterns = [
        r"\bcrash(?:es|ed|ing)?\b",
        r"\b(not\s+)?responding\b",
        r"\bfreeze(?:s|d|ing)?\b",
        r"\bhangs?\b",
        r"\bbuffer(?:ing)?\b",
        r"won'?t\s+(?:load|play|open)",
        r"\bnot\s+(?:loading|playing|opening)\b",
        r"\b(no|missing)\s+sound\b",
        r"\bsound\s+(?:issue|problem|low|distorted)\b",
        r"\baudio\s+(?:issue|problem|not\s+playing|cuts?\s+out|drop(?:s|ping))\b",
        r"\bkeeps?\s+(?:stopping|pausing|closing)\b",
        r"\bplayback\b",
        r"\b(?:download|downloading)\s+(?:failed|error|problem|issues?|won'?t|not)\b",
        r"\boffline\s+(?:download|playback|listening)\b",
        r"\b(epi(?:sode)?s?\s+)?jump(?:s|ing)?\b",
        r"\bskipp(?:ing|ed|s)\b",
        r"\brepeat(?:s|ing)?\s+episode\b",
        r"\bslow\s+stream(?:ing)?\b",
        r"\bstutter(?:s|ing)?\b",
        r"\blag(?:s|gy|ging)?\b",
    ]

    if any(re.search(p, text_l) for p in patterns):
        return True

    # Language-aware quick checks for common phrases we saw in data
    hindi_terms = [
        "play nahi ho raha",  # not playing
        "audio ya video dono nahi chal rahe",  # neither audio nor video playing
        "video start nahi hota",  # video does not start
    ]
    if any(term in text_l for term in hindi_terms):
        return True

    spanish_terms = [
        "no reproduce",  # does not play
        "no carga",  # does not load
    ]
    if any(term in text_l for term in spanish_terms):
        return True

    return False


def filter_rows(rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    filtered: List[Dict[str, str]] = []
    for row in rows:
        categories = row.get("categories", "")
        subcategories = row.get("subcategories", "")
        review_text = row.get("review_text", "")
        if is_playback_or_performance(categories, subcategories, review_text):
            filtered.append(row)
    return filtered


def main() -> None:
    if not os.path.exists(INPUT_CSV):
        raise SystemExit(f"Input CSV not found: {INPUT_CSV}")

    with open(INPUT_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = [
            {k: normalize(v) for k, v in r.items()}  # normalize whitespace
            for r in reader
        ]

    filtered = filter_rows(rows)

    # Save JSON
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_JSON, "w", encoding="utf-8") as jf:
        json.dump(filtered, jf, ensure_ascii=False, indent=2)

    # Save CSV with a consistent field order
    fieldnames = [
        "day_index",
        "week_bucket",
        "week_label",
        "line_index",
        "reviewer",
        "rating",
        "sentiment",
        "language",
        "categories",
        "subcategories",
        "review_text",
    ]
    with open(OUT_CSV, "w", encoding="utf-8", newline="") as cf:
        writer = csv.DictWriter(cf, fieldnames=fieldnames)
        writer.writeheader()
        for r in filtered:
            writer.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"Filtered reviews: {len(filtered)}")
    print(OUT_JSON)
    print(OUT_CSV)


if __name__ == "__main__":
    main()

