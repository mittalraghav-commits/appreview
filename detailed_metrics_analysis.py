#!/usr/bin/env python3
import pandas as pd
import json
from collections import defaultdict
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta

# Load the existing analysis data
def load_analysis_data():
    # Load parsed reviews
    reviews_df = pd.read_csv('/workspace/analysis_output/parsed_reviews.csv')
    
    # Load trends data
    with open('/workspace/analysis_output/trends.json', 'r') as f:
        trends = json.load(f)
    
    # Load daily theme counts
    daily_themes = pd.read_csv('/workspace/analysis_output/daily_theme_counts.csv')
    
    # Load overall counts
    overall_themes = pd.read_csv('/workspace/analysis_output/overall_theme_counts.csv')
    overall_subcategories = pd.read_csv('/workspace/analysis_output/overall_subcategory_counts.csv')
    
    return reviews_df, trends, daily_themes, overall_themes, overall_subcategories

def create_enhanced_analysis():
    reviews_df, trends, daily_themes, overall_themes, overall_subcategories = load_analysis_data()
    
    # Enhanced analysis report
    report = []
    report.append("# Enhanced iOS Review Analysis - Detailed Metrics\n")
    
    # Overall Statistics
    report.append("## Overall Statistics")
    report.append(f"- **Total Reviews Analyzed**: {len(reviews_df):,}")
    report.append(f"- **Analysis Period**: {daily_themes['day_index'].min():.0f} to {daily_themes['day_index'].max():.0f} days")
    report.append(f"- **Average Reviews per Day**: {len(reviews_df) / (daily_themes['day_index'].max() - daily_themes['day_index'].min() + 1):.1f}")
    report.append("")
    
    # Top Issues Ranking
    report.append("## Top Issues Ranking by Volume")
    report.append("| Rank | Category | Count | Percentage | Critical Level |")
    report.append("|------|----------|-------|------------|----------------|")
    
    for idx, row in overall_themes.iterrows():
        pct = (row['count'] / len(reviews_df)) * 100
        if pct > 30:
            critical = "🔴 CRITICAL"
        elif pct > 15:
            critical = "🟡 HIGH"
        elif pct > 5:
            critical = "🟢 MEDIUM"
        else:
            critical = "⚪ LOW"
        report.append(f"| {idx+1} | {row['theme']} | {row['count']} | {pct:.1f}% | {critical} |")
    
    report.append("")
    
    # Subcategory Analysis
    report.append("## Detailed Subcategory Breakdown")
    
    # Group by main theme
    for theme in overall_themes['theme']:
        if theme == 'Other':
            continue
        theme_subs = overall_subcategories[overall_subcategories['theme'] == theme]
        if not theme_subs.empty:
            report.append(f"### {theme}")
            total_theme_count = theme_subs['count'].sum()
            for _, sub_row in theme_subs.iterrows():
                pct_of_theme = (sub_row['count'] / total_theme_count) * 100
                pct_of_total = (sub_row['count'] / len(reviews_df)) * 100
                report.append(f"- **{sub_row['subcategory']}**: {sub_row['count']} reviews ({pct_of_theme:.1f}% of {theme}, {pct_of_total:.1f}% of total)")
            report.append("")
    
    # Day-by-day anomaly analysis
    report.append("## Daily Anomaly Analysis")
    
    # Find days with highest z-scores
    anomaly_days = daily_themes[daily_themes['zscore_7'] > 2.0].sort_values('zscore_7', ascending=False)
    
    if not anomaly_days.empty:
        report.append("### Statistical Anomalies (Z-score > 2.0)")
        report.append("| Day | Theme | Count | Z-Score | Severity |")
        report.append("|-----|-------|-------|---------|----------|")
        
        for _, row in anomaly_days.head(15).iterrows():
            if row['zscore_7'] > 3.0:
                severity = "🚨 EXTREME"
            elif row['zscore_7'] > 2.5:
                severity = "🔴 SEVERE"
            else:
                severity = "🟡 NOTABLE"
            report.append(f"| {row['day_index']:.0f} | {row['theme']} | {row['count']:.0f} | {row['zscore_7']:.2f} | {severity} |")
    
    report.append("")
    
    # Growth trends analysis
    report.append("## Growth Trend Analysis")
    
    # Calculate week-over-week growth for themes
    weekly_data = defaultdict(list)
    for day in range(1, int(daily_themes['day_index'].max()) + 1):
        week = (day - 1) // 7 + 1
        day_data = daily_themes[daily_themes['day_index'] == day]
        for _, row in day_data.iterrows():
            weekly_data[week].append({
                'theme': row['theme'],
                'count': row['count']
            })
    
    # Calculate weekly totals
    weekly_totals = {}
    for week, data in weekly_data.items():
        theme_counts = defaultdict(int)
        for item in data:
            theme_counts[item['theme']] += item['count']
        weekly_totals[week] = dict(theme_counts)
    
    # Calculate growth rates
    if len(weekly_totals) >= 2:
        first_week = min(weekly_totals.keys())
        last_week = max(weekly_totals.keys())
        
        report.append(f"### Week {first_week} vs Week {last_week} Growth")
        report.append("| Theme | Week 1 | Last Week | Growth | Trend |")
        report.append("|-------|--------|-----------|---------|-------|")
        
        for theme in overall_themes['theme']:
            if theme == 'Other':
                continue
            week1_count = weekly_totals.get(first_week, {}).get(theme, 0)
            last_week_count = weekly_totals.get(last_week, {}).get(theme, 0)
            
            if week1_count > 0:
                growth = ((last_week_count - week1_count) / week1_count) * 100
            else:
                growth = 100 if last_week_count > 0 else 0
            
            if growth > 50:
                trend = "📈 RISING"
            elif growth > 0:
                trend = "↗️ GROWING"
            elif growth > -25:
                trend = "➡️ STABLE"
            else:
                trend = "📉 DECLINING"
                
            report.append(f"| {theme} | {week1_count} | {last_week_count} | {growth:+.1f}% | {trend} |")
    
    report.append("")
    
    # Sentiment analysis by category
    report.append("## Sentiment Distribution by Category")
    
    sentiment_analysis = reviews_df.groupby(['categories', 'sentiment']).size().unstack(fill_value=0)
    
    if not sentiment_analysis.empty:
        report.append("| Category | Negative | Neutral | Positive | Neg % |")
        report.append("|----------|----------|---------|----------|-------|")
        
        for category in sentiment_analysis.index:
            if 'Monetization' in category or 'Content' in category or 'Playback' in category:
                total = sentiment_analysis.loc[category].sum()
                neg = sentiment_analysis.loc[category].get('Negative', 0)
                neu = sentiment_analysis.loc[category].get('Neutral', 0) 
                pos = sentiment_analysis.loc[category].get('Positive', 0)
                neg_pct = (neg / total * 100) if total > 0 else 0
                
                report.append(f"| {category} | {neg} | {neu} | {pos} | {neg_pct:.1f}% |")
    
    report.append("")
    
    # Critical recommendations
    report.append("## Critical Action Items")
    report.append("### 🚨 Immediate Actions (Next 7 Days)")
    report.append("1. **Investigate Day 21 Incident**: Root cause analysis of the massive spike")
    report.append("2. **Emergency Pricing Review**: Address 'too expensive' complaints (301 reviews)")
    report.append("3. **Ad Frequency Audit**: Implement immediate caps on ad frequency")
    report.append("4. **Support Team Scale-Up**: Address 40% increase in support complaints")
    report.append("")
    
    report.append("### 🔧 Short-term Fixes (Next 30 Days)")
    report.append("1. **AI Voice Quality Improvement**: Address 297 voice quality complaints")
    report.append("2. **App Stability Focus**: Continue reducing crash-related issues")
    report.append("3. **Billing System Review**: Fix unauthorized charge issues")
    report.append("4. **Content Unlock Strategy**: Revise episode unlock timing")
    report.append("")
    
    report.append("### 📈 Strategic Initiatives (Next 90 Days)")
    report.append("1. **Monetization Strategy Overhaul**: New pricing tiers and value propositions")
    report.append("2. **Localization Expansion**: Add Hindi, Telugu, and other regional languages")
    report.append("3. **Premium Experience Design**: Reduce ads for paying users")
    report.append("4. **Predictive Analytics Implementation**: Early warning system for issues")
    report.append("")
    
    # Success metrics
    report.append("## Success Metrics & KPIs")
    report.append("### Primary KPIs")
    report.append("- **Monetization Complaint Reduction**: Target 50% reduction in coin/pricing complaints")
    report.append("- **Content Quality Score**: Reduce AI voice complaints by 40%")
    report.append("- **Support Response Improvement**: <24h response time for 90% of tickets")
    report.append("- **App Stability**: Reduce crash-related complaints by 60%")
    report.append("")
    
    report.append("### Secondary KPIs") 
    report.append("- **Ad Experience Score**: Reduce ad-related complaints by 35%")
    report.append("- **Localization Coverage**: Add 3 new languages based on demand")
    report.append("- **User Retention**: Monitor impact of changes on retention rates")
    report.append("- **Review Sentiment**: Improve overall sentiment score by 20%")
    report.append("")
    
    return '\n'.join(report)

def create_summary_tables():
    """Create CSV summary tables for easy reference"""
    reviews_df, trends, daily_themes, overall_themes, overall_subcategories = load_analysis_data()
    
    # Priority matrix
    priority_matrix = []
    
    for _, row in overall_themes.iterrows():
        if row['theme'] == 'Other':
            continue
            
        pct = (row['count'] / len(reviews_df)) * 100
        
        # Assign priority based on volume and growth
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
            
        priority_matrix.append({
            'Theme': row['theme'],
            'Count': row['count'],
            'Percentage': f"{pct:.1f}%",
            'Priority': priority,
            'Business_Impact': impact
        })
    
    priority_df = pd.DataFrame(priority_matrix)
    priority_df.to_csv('/workspace/analysis_output/priority_matrix.csv', index=False)
    
    # Anomaly summary
    anomalies = daily_themes[daily_themes['zscore_7'] > 2.0].copy()
    anomalies['Severity'] = anomalies['zscore_7'].apply(
        lambda x: 'EXTREME' if x > 3.0 else 'SEVERE' if x > 2.5 else 'NOTABLE'
    )
    anomalies[['day_index', 'theme', 'count', 'zscore_7', 'Severity']].to_csv(
        '/workspace/analysis_output/critical_anomalies.csv', index=False
    )
    
    print("Enhanced analysis complete. Files generated:")
    print("- /workspace/analysis_output/priority_matrix.csv")
    print("- /workspace/analysis_output/critical_anomalies.csv")
    print("- Enhanced analysis written to detailed_metrics_analysis.md")

if __name__ == "__main__":
    # Generate enhanced analysis
    enhanced_report = create_enhanced_analysis()
    
    # Write to file
    with open('/workspace/detailed_metrics_analysis.md', 'w') as f:
        f.write(enhanced_report)
    
    # Create summary tables
    create_summary_tables()
    
    print("Analysis complete!")