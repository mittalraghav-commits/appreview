#!/usr/bin/env python3
"""
Android Daily Trends Analysis - Detailed Day-on-Day Analysis
"""

import csv
import json
from collections import defaultdict, Counter

def analyze_daily_trends():
    """Analyze daily trends with detailed insights"""
    
    # Read the daily trends data
    daily_data = defaultdict(lambda: defaultdict(int))
    
    with open('/workspace/android_analysis_output/android_daily_trends.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            day = int(row['day'])
            category = row['category']
            count = int(row['count'])
            daily_data[day][category] = count
    
    # Read anomalies
    anomalies = []
    with open('/workspace/android_analysis_output/android_anomalies.csv', 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            anomalies.append({
                'day': int(row['day']),
                'category': row['category'],
                'count': int(row['count']),
                'z_score': float(row['z_score']),
                'increase_pct': float(row['increase_pct'])
            })
    
    # Analyze trends
    print("=== ANDROID DAILY TRENDS ANALYSIS ===\n")
    
    # Find days with highest overall activity
    daily_totals = {}
    for day, categories in daily_data.items():
        daily_totals[day] = sum(categories.values())
    
    top_days = sorted(daily_totals.items(), key=lambda x: x[1], reverse=True)[:10]
    
    print("📈 TOP 10 HIGHEST ACTIVITY DAYS:")
    for i, (day, total) in enumerate(top_days, 1):
        categories_breakdown = []
        for cat, count in daily_data[day].items():
            if count > 0:
                categories_breakdown.append(f"{cat}: {count}")
        print(f"{i:2}. Day {day:3}: {total:2} complaints - {', '.join(categories_breakdown)}")
    
    print("\n🚨 TOP ANOMALOUS DAYS (Highest Z-scores):")
    top_anomalies = sorted(anomalies, key=lambda x: x['z_score'], reverse=True)[:15]
    
    for i, anomaly in enumerate(top_anomalies, 1):
        print(f"{i:2}. Day {anomaly['day']:3}: {anomaly['category']} - {anomaly['count']} complaints "
              f"(Z-score: {anomaly['z_score']:.2f}, +{anomaly['increase_pct']:.0f}%)")
    
    # Category-wise trend analysis
    print("\n📊 CATEGORY TREND ANALYSIS:")
    
    category_stats = defaultdict(list)
    for day, categories in daily_data.items():
        for category, count in categories.items():
            category_stats[category].append((day, count))
    
    for category, data in category_stats.items():
        if len(data) > 5:  # Only analyze categories with sufficient data
            total_complaints = sum(count for day, count in data)
            active_days = len([count for day, count in data if count > 0])
            max_day_count = max(count for day, count in data)
            max_day = [day for day, count in data if count == max_day_count][0]
            
            print(f"\n{category}:")
            print(f"  Total complaints: {total_complaints}")
            print(f"  Active days: {active_days}")
            print(f"  Peak day: Day {max_day} ({max_day_count} complaints)")
            
            # Find recent trends (last 50 days with data)
            recent_data = [(day, count) for day, count in data if day >= max(day for day, count in data) - 50]
            if len(recent_data) > 3:
                recent_total = sum(count for day, count in recent_data)
                print(f"  Recent activity (last 50 days): {recent_total} complaints")
    
    # Weekly pattern analysis
    print("\n📅 WEEKLY PATTERN ANALYSIS:")
    
    # Group days into weeks (assuming 7-day weeks)
    weekly_data = defaultdict(lambda: defaultdict(int))
    for day, categories in daily_data.items():
        week = day // 7
        for category, count in categories.items():
            weekly_data[week][category] += count
    
    # Find weeks with highest activity
    weekly_totals = {}
    for week, categories in weekly_data.items():
        weekly_totals[week] = sum(categories.values())
    
    top_weeks = sorted(weekly_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    
    print("Top 5 Most Active Weeks:")
    for i, (week, total) in enumerate(top_weeks, 1):
        start_day = week * 7
        end_day = start_day + 6
        print(f"{i}. Week {week} (Days {start_day}-{end_day}): {total} complaints")
        
        # Show breakdown
        for category, count in weekly_data[week].items():
            if count > 0:
                print(f"   - {category}: {count}")
    
    # Seasonal analysis (if we have enough data)
    print("\n🗓️ SEASONAL ANALYSIS:")
    
    # Group by quarters (90-day periods)
    quarterly_data = defaultdict(lambda: defaultdict(int))
    for day, categories in daily_data.items():
        quarter = day // 90
        for category, count in categories.items():
            quarterly_data[quarter][category] += count
    
    print("Quarterly Breakdown:")
    for quarter in sorted(quarterly_data.keys()):
        start_day = quarter * 90
        end_day = start_day + 89
        total = sum(quarterly_data[quarter].values())
        print(f"Quarter {quarter} (Days {start_day}-{end_day}): {total} complaints")
        
        # Top issues in this quarter
        top_issues = sorted(quarterly_data[quarter].items(), key=lambda x: x[1], reverse=True)[:3]
        for category, count in top_issues:
            if count > 0:
                print(f"   - {category}: {count}")
    
    # Growth rate analysis
    print("\n📈 GROWTH RATE ANALYSIS:")
    
    # Compare first half vs second half of data
    max_day = max(daily_data.keys())
    mid_point = max_day // 2
    
    first_half_totals = defaultdict(int)
    second_half_totals = defaultdict(int)
    
    for day, categories in daily_data.items():
        for category, count in categories.items():
            if day <= mid_point:
                first_half_totals[category] += count
            else:
                second_half_totals[category] += count
    
    print(f"Comparing First Half (Days 0-{mid_point}) vs Second Half (Days {mid_point+1}-{max_day}):")
    
    for category in set(list(first_half_totals.keys()) + list(second_half_totals.keys())):
        first_count = first_half_totals[category]
        second_count = second_half_totals[category]
        
        if first_count > 0:
            growth_rate = ((second_count - first_count) / first_count) * 100
            trend = "📈" if growth_rate > 20 else "📉" if growth_rate < -20 else "➡️"
            print(f"{trend} {category}: {first_count} → {second_count} ({growth_rate:+.1f}%)")
        elif second_count > 0:
            print(f"🆕 {category}: 0 → {second_count} (New issue)")

if __name__ == "__main__":
    analyze_daily_trends()