#!/usr/bin/env python3
import re
import os
import sys
import json
import csv
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple


SOURCE_FILE = "/workspace/App reviews dump - Sheet1.csv"
OUTPUT_DIR = "/workspace/analysis_output"


# Be lenient: accept any content between stars and sentiment, focus on 'by <name>' and sentiment token
STAR_LINE_RE = re.compile(r"★+.*?\bby\s*(.+?)\s*·\s*(Negative|Positive|Neutral)", re.IGNORECASE)
WEEKLY_SUMMARY_RE = re.compile(r"^Weekly Summary for\s*(.+?)\s*$")
APBOT_HEADER_INLINE_RE = re.compile(r"^Appbot: .*?APP\s+(\d{1,2}):(\d{2})\s*(AM|PM)\s*$")
TIME_ONLY_RE = re.compile(r"^(\d{1,2}):(\d{2})\s*$")
LANG_LINE_RE = re.compile(r"^(English|Spanish|German|French|Hindi|Finnish|Danish|Portuguese|Italian|Dutch|Polish|Turkish|Arabic|Russian|Indonesian|Malay|Thai|Vietnamese|Chinese)\s*·\s*Google Play\s*$", re.IGNORECASE)


@dataclass
class Review:
    day_index: int
    line_index: int
    reviewer: Optional[str]
    rating: Optional[int]
    sentiment: Optional[str]
    review_text: str
    language: Optional[str]
    week_bucket: Optional[int]
    week_label: Optional[str]
    categories: List[str]
    subcategories: List[str]


def ensure_output_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def read_lines(path: str) -> List[str]:
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        return [line.rstrip("\n") for line in f]


def parse_reviews(lines: List[str]) -> Tuple[List[Review], List[Tuple[int, str]]]:
    reviews: List[Review] = []
    weekly_anchors: List[Tuple[int, str]] = []  # (line_index, label)

    current_language: Optional[str] = None
    current_day_index = 1
    last_star_block: Optional[Dict] = None
    i = 0
    line_count = len(lines)

    while i < line_count:
        line = lines[i].strip()

        # Detect weekly summary anchors
        m_week = WEEKLY_SUMMARY_RE.match(line)
        if m_week:
            weekly_anchors.append((i, m_week.group(1)))
            i += 1
            continue

        # Detect appbot inline header with time; use 12:xx AM as day boundary
        m_hdr = APBOT_HEADER_INLINE_RE.match(line)
        if m_hdr:
            hour = int(m_hdr.group(1))
            minute = int(m_hdr.group(2))
            ampm = m_hdr.group(3)
            if ampm.upper() == "AM" and hour == 12:
                # Heuristic: treat 12:xx AM as a new day boundary
                current_day_index += 1
            i += 1
            continue

        # Time-only lines might appear; they don't change state significantly
        if TIME_ONLY_RE.match(line):
            i += 1
            continue

        # Language lines
        m_lang = LANG_LINE_RE.match(line)
        if m_lang:
            current_language = m_lang.group(1)
            i += 1
            continue

        # Star line indicates start of a review block
        m_star = STAR_LINE_RE.search(line)
        if m_star:
            reviewer = m_star.group(1).strip()
            sentiment = m_star.group(2)

            rating = line.count("★")

            # The review text is usually the next non-empty line(s) until a blank or a known separator
            review_lines: List[str] = []
            j = i + 1

            # Support translated blocks: if we encounter a dashed separator followed by 'English Translation', capture translated text block
            captured_translation = False
            while j < line_count:
                nxt = lines[j].strip()
                if nxt == "":
                    # blank line terminates block in the secondary export; in CSV-like export, we may not see blanks often
                    break
                # End of this block if next star line or header or weekly summary
                if STAR_LINE_RE.search(nxt) or APBOT_HEADER_INLINE_RE.match(nxt) or WEEKLY_SUMMARY_RE.match(nxt) or TIME_ONLY_RE.match(nxt) or LANG_LINE_RE.match(nxt):
                    break
                # Stop at reply/permalink marker line
                if "reply |" in nxt.lower():
                    break
                # Translation block support
                if nxt.startswith("-------------------"):
                    # Look ahead for 'English Translation' line
                    if j + 1 < line_count and lines[j + 1].strip().lower().startswith("english translation"):
                        # Skip the 'English Translation' line
                        j += 2
                        # Capture until next dashed separator or block end
                        trans_lines: List[str] = []
                        while j < line_count:
                            tline = lines[j].strip()
                            if tline.startswith("-------------------"):
                                captured_translation = True
                                break
                            # stop when encountering next block markers
                            if STAR_LINE_RE.match(tline) or APBOT_HEADER_INLINE_RE.match(tline) or WEEKLY_SUMMARY_RE.match(tline) or TIME_ONLY_RE.match(tline) or LANG_LINE_RE.match(tline):
                                captured_translation = True
                                j -= 1  # step back to let outer loop break on this marker
                                break
                            trans_lines.append(tline)
                            j += 1
                        review_lines = trans_lines if trans_lines else review_lines
                    # Move past dashed separator closing if present
                    j += 1
                    # Continue; the outer break conditions will handle further markers
                    continue
                else:
                    review_lines.append(nxt)
                    j += 1

            review_text = " ".join(review_lines).strip()

            reviews.append(
                Review(
                    day_index=current_day_index,
                    line_index=i,
                    reviewer=reviewer if reviewer else None,
                    rating=rating,
                    sentiment=sentiment,
                    review_text=review_text,
                    language=current_language,
                    week_bucket=None,
                    week_label=None,
                    categories=[],
                    subcategories=[],
                )
            )
            i = j
            continue

        # Default advance
        i += 1

    return reviews, weekly_anchors


def build_taxonomy() -> Dict[str, Dict[str, List[str]]]:
    # Keyword-based taxonomy; simple lowercase string contains checks
    return {
        "Monetization & Pricing": {
            "Too expensive / high coin cost": [
                "expensive", "too expensive", "cost", "money pit", "coins", "coin", "price", "pricing", "costly", "paywall", "micro transaction", "microtransaction", "overpriced"
            ],
            "Subscription needed / request": [
                "subscription", "monthly", "subscribe", "abo", "abonnement"
            ],
            "Coin loss / inconsistency": [
                "coins back", "coin back", "taking coins", "stole coins", "coins were stolen", "lost coins", "coin balance"
            ],
            "Ads gating / too many ads": [
                "too many ads", "ads", "adverts", "advertisements", "watch ads", "forced ads", "2 minutes of ads", "20 ads", "ad block", "ad is"
            ],
            "Misleading ads / bait-and-switch": [
                "misleading", "bait", "bait-and-switch", "facebook ads", "ad has nothing to do", "lie", "fake ads", "ad lies", "false advertising"
            ],
            "Unauthorized charge / auto pay": [
                "charged without", "without my knowledge", "auto pay", "auto-pay", "auto debit", "unauthorized", "deducted", "auto charge", "rupees deducted", "599"
            ],
        },
        "Playback & Performance": {
            "Buffering / won't load": [
                "buffering", "won't load", "cant load", "can't load", "not load", "loading only", "keep loading", "unable to open", "spinning", "spin", "won't open", "couldn't get it to open"
            ],
            "Crashes / app not working": [
                "crash", "crashes", "stops", "not working", "doesn't work", "stopped working", "bug", "buggy"
            ],
            "Playback jumps / episode switching": [
                "jumping back", "switching", "skipping", "skip", "next episode automatically", "starts between", "scroll 100s", "bookmark lost"
            ],
            "Offline / download issues": [
                "download", "offline", "downloaded"
            ],
        },
        "Content & UX": {
            "Story mismatch vs ads": [
                "nothing like", "nothing to do with the ad", "story changes", "the ad has nothing to do"
            ],
            "Visual vs audio expectation": [
                "video", "visual", "picture", "image with background audio", "not a episode on screen"
            ],
            "AI voices / quality": [
                "ai", "ai-generated", "voice", "narrator", "audio quality", "sound quality"
            ],
            "Too slow unlock / few free episodes": [
                "unlock slowly", "free episodes", "only one free episode", "one free episode", "reduce the free episodes", "wait for free episodes"
            ],
            "Notifications / interruptions": [
                "notification", "notifications"
            ],
        },
        "Payments & Support": {
            "Billing / refund / trial issues": [
                "refund", "trial", "free trial", "charged", "payment failed", "billing", "invoice", "receipts"
            ],
            "Support unresponsive": [
                "support", "no response", "didn't respond", "useless"
            ],
        },
        "Localization & Availability": {
            "Missing languages / dubbing": [
                "telugu", "hindi", "language", "translate", "translation", "dub", "dubbing"
            ],
            "Region restrictions": [
                "not available", "region", "country"
            ],
        },
    }


def categorize_text(text: str, taxonomy: Dict[str, Dict[str, List[str]]]) -> Tuple[List[str], List[str]]:
    text_l = text.lower()
    categories: List[str] = []
    subcategories: List[str] = []
    for cat, subs in taxonomy.items():
        matched_any = False
        for sub, keywords in subs.items():
            for kw in keywords:
                if kw in text_l:
                    if cat not in categories:
                        categories.append(cat)
                    if sub not in subcategories:
                        subcategories.append(sub)
                    matched_any = True
                    break
        # if matched_any:  # allow multiple subs per category; don't break
        #     pass
    return categories, subcategories


def assign_weeks_by_stride(max_day_index: int, stride: int = 7) -> Dict[int, Tuple[int, str]]:
    mapping: Dict[int, Tuple[int, str]] = {}
    week_num = 1
    for d in range(1, max_day_index + 1):
        week_bucket = (d - 1) // stride + 1
        if week_bucket != week_num:
            week_num = week_bucket
        mapping[d] = (week_bucket, f"Week {week_bucket}")
    return mapping


def compute_trends(reviews: List[Review]) -> Dict:
    # Aggregate per day and per week
    by_day_cat = defaultdict(lambda: defaultdict(int))  # day -> category -> count
    by_week_cat = defaultdict(lambda: defaultdict(int))  # week -> category -> count
    by_day_sub = defaultdict(lambda: defaultdict(int))
    by_week_sub = defaultdict(lambda: defaultdict(int))
    day_totals = Counter()
    week_totals = Counter()

    max_day = 0
    for r in reviews:
        max_day = max(max_day, r.day_index)
    week_map = assign_weeks_by_stride(max_day)

    for r in reviews:
        week_bucket, week_label = week_map.get(r.day_index, (None, None))
        r.week_bucket = week_bucket
        r.week_label = week_label
        day_totals[r.day_index] += 1
        if week_bucket is not None:
            week_totals[week_bucket] += 1
        for cat in r.categories:
            by_day_cat[r.day_index][cat] += 1
            if week_bucket is not None:
                by_week_cat[week_bucket][cat] += 1
        for sub in r.subcategories:
            by_day_sub[r.day_index][sub] += 1
            if week_bucket is not None:
                by_week_sub[week_bucket][sub] += 1

    return {
        "by_day_cat": {str(k): dict(v) for k, v in by_day_cat.items()},
        "by_week_cat": {str(k): dict(v) for k, v in by_week_cat.items()},
        "by_day_sub": {str(k): dict(v) for k, v in by_day_sub.items()},
        "by_week_sub": {str(k): dict(v) for k, v in by_week_sub.items()},
        "day_totals": {str(k): v for k, v in day_totals.items()},
        "week_totals": {str(k): v for k, v in week_totals.items()},
        "max_day": max_day,
    }


def compute_growth_signals(by_week: Dict[str, Dict[str, int]], week_totals: Dict[str, int]) -> Dict[str, Dict[str, float]]:
    # Compare first half vs last half share per category/subcategory
    weeks_sorted = sorted(int(w) for w in by_week.keys())
    if not weeks_sorted:
        return {}
    mid = len(weeks_sorted) // 2
    early = weeks_sorted[:mid]
    late = weeks_sorted[mid:]

    def share_avg(keys: List[int], cat: str) -> float:
        shares = []
        for w in keys:
            total = week_totals.get(str(w), 0)
            if total <= 0:
                continue
            count = by_week.get(str(w), {}).get(cat, 0)
            shares.append(count / total)
        return sum(shares) / len(shares) if shares else 0.0

    # Collect all categories across weeks
    cats = set()
    for w in by_week.values():
        cats.update(w.keys())

    result: Dict[str, Dict[str, float]] = {}
    for cat in cats:
        early_share = share_avg(early, cat)
        late_share = share_avg(late, cat)
        delta = late_share - early_share
        pct_change = (delta / early_share * 100.0) if early_share > 0 else (late_share * 100.0)
        result[cat] = {
            "early_share": early_share,
            "late_share": late_share,
            "delta_share": delta,
            "pct_change": pct_change,
        }
    return result


def write_outputs(reviews: List[Review], trends: Dict, taxonomy: Dict[str, Dict[str, List[str]]]) -> None:
    ensure_output_dir(OUTPUT_DIR)

    # Parsed reviews CSV
    parsed_csv = os.path.join(OUTPUT_DIR, "parsed_reviews.csv")
    with open(parsed_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["day_index", "week_bucket", "week_label", "line_index", "reviewer", "rating", "sentiment", "language", "categories", "subcategories", "review_text"])
        for r in reviews:
            w.writerow([
                r.day_index,
                r.week_bucket,
                r.week_label,
                r.line_index,
                r.reviewer or "",
                r.rating or "",
                r.sentiment or "",
                r.language or "",
                ";".join(r.categories),
                ";".join(r.subcategories),
                r.review_text,
            ])

    # Trends JSON
    with open(os.path.join(OUTPUT_DIR, "trends.json"), "w", encoding="utf-8") as f:
        json.dump(trends, f, indent=2)

    # Growth signals
    cat_growth = compute_growth_signals(trends["by_week_cat"], trends["week_totals"])
    sub_growth = compute_growth_signals(trends["by_week_sub"], trends["week_totals"])

    # Top categories latest week
    if trends["week_totals"]:
        latest_week = max(int(w) for w in trends["week_totals"].keys())
        latest_cat = trends["by_week_cat"].get(str(latest_week), {})
        latest_sub = trends["by_week_sub"].get(str(latest_week), {})
    else:
        latest_week = None
        latest_cat = {}
        latest_sub = {}

    # Markdown report
    report_md = os.path.join(OUTPUT_DIR, "report.md")
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("## Review Analysis Summary\n\n")
        f.write(f"Total reviews parsed: {len(reviews)}\n\n")
        f.write("### Latest Week Top Categories\n")
        for cat, cnt in sorted(latest_cat.items(), key=lambda x: x[1], reverse=True)[:10]:
            f.write(f"- {cat}: {cnt}\n")
        f.write("\n### Latest Week Top Subcategories\n")
        for sub, cnt in sorted(latest_sub.items(), key=lambda x: x[1], reverse=True)[:12]:
            f.write(f"- {sub}: {cnt}\n")

        f.write("\n### Emerging vs Long-standing (Categories)\n")
        # classify emerging/declining/stable
        emg, dec, st = [], [], []
        for cat, g in cat_growth.items():
            if g["pct_change"] >= 25 and g["late_share"] >= 0.08:
                emg.append((cat, g))
            elif g["pct_change"] <= -25 and g["early_share"] >= 0.08:
                dec.append((cat, g))
            else:
                st.append((cat, g))
        if emg:
            f.write("- Increasing:\n")
            for cat, g in sorted(emg, key=lambda x: x[1]["pct_change"], reverse=True):
                f.write(f"  - {cat}: {g['early_share']:.1%} -> {g['late_share']:.1%} ({g['pct_change']:.0f}%)\n")
        if dec:
            f.write("- Declining:\n")
            for cat, g in sorted(dec, key=lambda x: x[1]["pct_change"]):
                f.write(f"  - {cat}: {g['early_share']:.1%} -> {g['late_share']:.1%} ({g['pct_change']:.0f}%)\n")
        if st:
            f.write("- Stable/Mixed:\n")
            for cat, g in sorted(st, key=lambda x: -abs(x[1]["pct_change"]))[:10]:
                f.write(f"  - {cat}: {g['early_share']:.1%} -> {g['late_share']:.1%} ({g['pct_change']:.0f}%)\n")

        f.write("\n### Notes\n")
        f.write("- Day-by-day trends are computed by chronological buckets due to sparse explicit dates in the export. Weekly aggregation uses consecutive 7-day windows.\n")
        f.write("- Categories are assigned via keyword matching; multiple categories can apply per review.\n")


def main() -> None:
    if not os.path.exists(SOURCE_FILE):
        print(f"Source file not found: {SOURCE_FILE}", file=sys.stderr)
        sys.exit(1)
    lines = read_lines(SOURCE_FILE)
    reviews, weekly_anchors = parse_reviews(lines)
    taxonomy = build_taxonomy()

    # Categorize
    for r in reviews:
        cats, subs = categorize_text(r.review_text, taxonomy)
        r.categories = cats
        r.subcategories = subs

    trends = compute_trends(reviews)
    write_outputs(reviews, trends, taxonomy)
    print(f"Parsed {len(reviews)} reviews. Output in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()

