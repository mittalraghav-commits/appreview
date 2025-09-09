#!/usr/bin/env python3
import csv
import json
from collections import defaultdict

def load_csv_data(filename):
    """Load CSV data into list of dictionaries"""
    data = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                data.append(row)
    except FileNotFoundError:
        print(f"File {filename} not found")
        return []
    return data

def create_enhanced_analysis():
    # Load existing data
    overall_themes = load_csv_data('/workspace/analysis_output/overall_theme_counts.csv')
    overall_subcategories = load_csv_data('/workspace/analysis_output/overall_subcategory_counts.csv')
    daily_themes = load_csv_data('/workspace/analysis_output/daily_theme_counts.csv')
    anomalies = load_csv_data('/workspace/analysis_output/anomalies_daily_theme.csv')
    
    # Calculate total reviews
    total_reviews = sum(int(row['count']) for row in overall_themes if row['theme'] != 'Other')
    
    report = []
    report.append("# Enhanced iOS Review Analysis - Detailed Metrics\n")
    
    # Overall Statistics
    report.append("## Overall Statistics")
    report.append(f"- **Total Reviews Analyzed**: {total_reviews:,}")
    
    if daily_themes:
        max_day = max(float(row['day_index']) for row in daily_themes if row['day_index'])
        min_day = min(float(row['day_index']) for row in daily_themes if row['day_index'])
        avg_per_day = total_reviews / (max_day - min_day + 1)
        report.append(f"- **Analysis Period**: {min_day:.0f} to {max_day:.0f} days")
        report.append(f"- **Average Reviews per Day**: {avg_per_day:.1f}")
    
    report.append("")
    
    # Top Issues Ranking
    report.append("## Top Issues Ranking by Volume")
    report.append("| Rank | Category | Count | Percentage | Critical Level |")
    report.append("|------|----------|-------|------------|----------------|")
    
    # Sort themes by count
    sorted_themes = sorted(overall_themes, key=lambda x: int(x['count']), reverse=True)
    
    for idx, row in enumerate(sorted_themes):
        if row['theme'] == 'Other':
            continue
        count = int(row['count'])
        pct = (count / total_reviews) * 100
        
        if pct > 30:
            critical = "🔴 CRITICAL"
        elif pct > 15:
            critical = "🟡 HIGH"
        elif pct > 5:
            critical = "🟢 MEDIUM"
        else:
            critical = "⚪ LOW"
        report.append(f"| {idx+1} | {row['theme']} | {count} | {pct:.1f}% | {critical} |")
    
    report.append("")
    
    # Subcategory Analysis
    report.append("## Detailed Subcategory Breakdown")
    
    # Group subcategories by theme
    theme_subcats = defaultdict(list)
    for sub_row in overall_subcategories:
        if sub_row['theme'] != 'Other':
            theme_subcats[sub_row['theme']].append(sub_row)
    
    for theme, subcats in theme_subcats.items():
        report.append(f"### {theme}")
        total_theme_count = sum(int(sub['count']) for sub in subcats)
        
        # Sort subcategories by count
        sorted_subcats = sorted(subcats, key=lambda x: int(x['count']), reverse=True)
        
        for sub_row in sorted_subcats:
            count = int(sub_row['count'])
            pct_of_theme = (count / total_theme_count) * 100 if total_theme_count > 0 else 0
            pct_of_total = (count / total_reviews) * 100
            report.append(f"- **{sub_row['subcategory']}**: {count} reviews ({pct_of_theme:.1f}% of {theme}, {pct_of_total:.1f}% of total)")
        report.append("")
    
    # Anomaly Analysis
    report.append("## Daily Anomaly Analysis")
    
    if anomalies:
        report.append("### Statistical Anomalies (Z-score > 2.0)")
        report.append("| Day | Theme | Count | Z-Score | Severity |")
        report.append("|-----|-------|-------|---------|----------|")
        
        # Sort by z-score
        sorted_anomalies = sorted(anomalies, key=lambda x: float(x['zscore_7']), reverse=True)
        
        for row in sorted_anomalies[:15]:
            zscore = float(row['zscore_7'])
            if zscore > 3.0:
                severity = "🚨 EXTREME"
            elif zscore > 2.5:
                severity = "🔴 SEVERE"
            else:
                severity = "🟡 NOTABLE"
            
            day = float(row['day_index'])
            count = float(row['count'])
            report.append(f"| {day:.0f} | {row['theme']} | {count:.0f} | {zscore:.2f} | {severity} |")
    
    report.append("")
    
    # Key Insights
    report.append("## Key Product Insights")
    
    # Find top issues
    top_theme = sorted_themes[0] if sorted_themes else None
    if top_theme and top_theme['theme'] != 'Other':
        top_count = int(top_theme['count'])
        top_pct = (top_count / total_reviews) * 100
        report.append(f"### 🚨 Primary Concern: {top_theme['theme']}")
        report.append(f"- **{top_count} complaints ({top_pct:.1f}% of all reviews)**")
        
        # Find top subcategory for this theme
        theme_subs = [sub for sub in overall_subcategories if sub['theme'] == top_theme['theme']]
        if theme_subs:
            top_sub = max(theme_subs, key=lambda x: int(x['count']))
            sub_count = int(top_sub['count'])
            sub_pct = (sub_count / top_count) * 100
            report.append(f"- Top subcategory: **{top_sub['subcategory']}** ({sub_count} reviews, {sub_pct:.1f}% of theme)")
    
    report.append("")
    
    # Critical recommendations
    report.append("## Critical Action Items")
    report.append("### 🚨 Immediate Actions (Next 7 Days)")
    
    # Based on data analysis, provide specific recommendations
    coins_issues = next((int(row['count']) for row in overall_themes if 'Coins' in row['theme']), 0)
    ads_issues = next((int(row['count']) for row in overall_themes if 'Ads' in row['theme']), 0)
    content_issues = next((int(row['count']) for row in overall_themes if 'Content' in row['theme']), 0)
    
    if coins_issues > 0:
        report.append(f"1. **Address Pricing Concerns**: {coins_issues} coin-related complaints need immediate pricing review")
    if content_issues > 0:
        report.append(f"2. **Content Quality Review**: {content_issues} content quality complaints require voice/format improvements")
    if ads_issues > 0:
        report.append(f"3. **Ad Experience Optimization**: {ads_issues} ad-related complaints need frequency/relevance fixes")
    
    # Find day with highest anomaly
    if anomalies:
        max_anomaly = max(anomalies, key=lambda x: float(x['zscore_7']))
        anomaly_day = float(max_anomaly['day_index'])
        report.append(f"4. **Investigate Day {anomaly_day:.0f} Incident**: Massive spike in {max_anomaly['theme']} complaints requires root cause analysis")
    
    report.append("")
    
    report.append("### 📈 Success Metrics")
    report.append("- **Primary KPI**: Reduce top complaint category by 50% within 30 days")
    report.append("- **Secondary KPI**: Prevent anomalous spikes (Z-score > 2.0) through monitoring")
    report.append("- **Tertiary KPI**: Improve overall review sentiment distribution")
    report.append("")
    
    # Priority matrix
    report.append("## Priority Action Matrix")
    report.append("| Priority | Theme | Impact | Effort | Action Required |")
    report.append("|----------|-------|---------|---------|-----------------|")
    
    for idx, row in enumerate(sorted_themes[:5]):
        if row['theme'] == 'Other':
            continue
        count = int(row['count'])
        pct = (count / total_reviews) * 100
        
        if pct > 30:
            priority = "P0"
            impact = "HIGH"
            effort = "HIGH"
            action = "Immediate overhaul"
        elif pct > 15:
            priority = "P1"
            impact = "MEDIUM"
            effort = "MEDIUM"
            action = "Strategic improvement"
        else:
            priority = "P2"
            impact = "LOW"
            effort = "LOW"
            action = "Incremental fixes"
            
        report.append(f"| {priority} | {row['theme']} | {impact} | {effort} | {action} |")
    
    return '\n'.join(report)

def create_priority_csv():
    """Create a priority matrix CSV"""
    overall_themes = load_csv_data('/workspace/analysis_output/overall_theme_counts.csv')
    total_reviews = sum(int(row['count']) for row in overall_themes if row['theme'] != 'Other')
    
    priority_data = []
    sorted_themes = sorted(overall_themes, key=lambda x: int(x['count']), reverse=True)
    
    for row in sorted_themes:
        if row['theme'] == 'Other':
            continue
        
        count = int(row['count'])
        pct = (count / total_reviews) * 100
        
        if pct > 30:
            priority = "P0 - CRITICAL"
            impact = "HIGH"
        elif pct > 15:
            priority = "P1 - HIGH"
            impact = "MEDIUM"
        elif pct > 5:
            priority = "P2 - MEDIUM"
            impact = "LOW"
        else:
            priority = "P3 - LOW"
            impact = "MINIMAL"
        
        priority_data.append([row['theme'], count, f"{pct:.1f}%", priority, impact])
    
    # Write priority matrix
    with open('/workspace/analysis_output/priority_matrix.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Theme', 'Count', 'Percentage', 'Priority', 'Business_Impact'])
        writer.writerows(priority_data)

if __name__ == "__main__":
    # Generate enhanced analysis
    enhanced_report = create_enhanced_analysis()
    
    # Write to file
    with open('/workspace/detailed_metrics_analysis.md', 'w') as f:
        f.write(enhanced_report)
    
    # Create priority CSV
    create_priority_csv()
    
    print("Enhanced analysis complete!")
    print("Files generated:")
    print("- /workspace/detailed_metrics_analysis.md")
    print("- /workspace/analysis_output/priority_matrix.csv")