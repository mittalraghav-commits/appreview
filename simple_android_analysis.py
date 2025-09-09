#!/usr/bin/env python3
"""
Android App Review Analysis Tool (No external dependencies)
Analyzes Android reviews for Pocket FM app to categorize issues and identify trends
"""

import re
import json
import csv
from datetime import datetime
from collections import defaultdict, Counter

class AndroidReviewAnalyzer:
    def __init__(self, csv_file_path):
        self.csv_file_path = csv_file_path
        self.reviews_data = []
        self.categories = {
            'Ads Related Issues': {
                'Too many ads / ads gating': [],
                'Misleading ads / bait-and-switch': [],
                'Ad quality / inappropriate ads': [],
                'Ad frequency / interruptions': [],
                'Forced ad watching': []
            },
            'Coins Related Issues': {
                'Too expensive / high coin cost': [],
                'Subscription needed / pricing model': [],
                'Too slow unlock / few free episodes': [],
                'Coin system confusing': [],
                'Unauthorized charges / billing issues': []
            },
            'Content Discovery Issues': {
                'Search / discoverability problems': [],
                'Poor recommendations / irrelevant suggestions': [],
                'Auto-starts other series': [],
                'Lack of new content': [],
                'Content organization / categories': []
            },
            'Listening Related Issues': {
                'Crashes / app not working': [],
                'Offline / download issues': [],
                'Buffering / won\'t load': [],
                'Playback jumps / episode switching': [],
                'Audio quality / sync issues': [],
                'Notifications / interruptions': []
            },
            'Content Quality Issues': {
                'AI voices / poor narration quality': [],
                'Visual vs audio expectation mismatch': [],
                'Story quality / content issues': [],
                'Translation / language issues': [],
                'Missing visual content': []
            },
            'User Experience Issues': {
                'Interface / navigation problems': [],
                'Login / account issues': [],
                'Settings / customization problems': [],
                'App performance / speed': [],
                'Update / compatibility issues': []
            },
            'Support & Service Issues': {
                'Support unresponsive': [],
                'Refund / billing disputes': [],
                'Account recovery problems': [],
                'Feature requests ignored': [],
                'Communication / transparency': []
            },
            'Localization Issues': {
                'Missing languages / dubbing': [],
                'Regional content availability': [],
                'Cultural adaptation issues': [],
                'Time zone / scheduling problems': []
            }
        }
        
    def load_and_parse_reviews(self):
        """Load and parse the CSV file to extract Android reviews"""
        print("Loading and parsing reviews...")
        
        with open(self.csv_file_path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # Split by Appbot timestamps to identify individual review sessions
        sessions = re.split(r'Appbot: App review alerts & repliesAPP \d+:\d+ [AP]M', content)
        
        day_counter = 0
        
        for session in sessions[1:]:  # Skip the first empty split
            lines = session.strip().split('\n')
            i = 0
            
            while i < len(lines):
                line = lines[i].strip()
                
                # Look for timestamp pattern (e.g., "12:26")
                time_match = re.match(r'^(\d{1,2}):(\d{2})$', line)
                if time_match and i + 1 < len(lines):
                    # Check if next line contains "Pocket FM: Audio Series (Google Play)"
                    next_line = lines[i + 1].strip()
                    if "Pocket FM: Audio Series (Google Play)" in next_line:
                        # Found an Android review
                        if i + 2 < len(lines):
                            rating_line = lines[i + 2].strip()
                            # Extract rating and reviewer info
                            rating_match = re.search(r'★+.*?by (.*?) ·', rating_line)
                            if rating_match:
                                reviewer = rating_match.group(1)
                                stars = rating_line.count('★')
                                
                                # Extract review text (next few lines until we hit reply/permalink/translate)
                                review_text = ""
                                j = i + 3
                                while j < len(lines) and not any(keyword in lines[j].lower() for keyword in ['reply', 'permalink', 'translate', 'english ·', 'spanish ·', 'german ·', 'danish ·']):
                                    if lines[j].strip() and not lines[j].strip().startswith('---'):
                                        if "Translation" not in lines[j]:
                                            review_text += lines[j].strip() + " "
                                    j += 1
                                
                                if review_text.strip():
                                    review = {
                                        'timestamp': f"{time_match.group(1)}:{time_match.group(2)}",
                                        'day': day_counter,
                                        'reviewer': reviewer,
                                        'stars': stars,
                                        'text': review_text.strip().strip('"'),
                                        'platform': 'Android'
                                    }
                                    self.reviews_data.append(review)
                
                i += 1
            
            day_counter += 1
            
        print(f"Parsed {len(self.reviews_data)} Android reviews across {day_counter} days")
        return self.reviews_data
    
    def categorize_review(self, review_text):
        """Categorize a single review into themes and sub-categories"""
        review_lower = review_text.lower()
        categories_found = []
        
        # Define keyword patterns for each category and subcategory
        patterns = {
            'Ads Related Issues': {
                'Too many ads / ads gating': ['too many ads', 'ads every', 'constant ads', 'ad after ad', 'ads gating', 'watch ads', 'ads to unlock', 'ads for coins', 'so many ads', 'ads everywhere'],
                'Misleading ads / bait-and-switch': ['misleading ad', 'false ad', 'ad different', 'nothing like ad', 'ad shows', 'facebook ad', 'advertisement lie', 'fake ad', 'ads lie'],
                'Ad quality / inappropriate ads': ['inappropriate ads', 'bad ads', 'annoying ads', 'stupid ads', 'ads suck', 'terrible ads'],
                'Ad frequency / interruptions': ['ads interrupt', 'ads break', 'ads pause', 'ads in middle', 'constant interruption'],
                'Forced ad watching': ['forced to watch', 'must watch ads', 'cant skip ads', 'skip ad', 'forced ads']
            },
            'Coins Related Issues': {
                'Too expensive / high coin cost': ['too expensive', 'cost too much', 'overpriced', 'ridiculous price', 'money pit', 'expensive coins', '$', 'euro', '€', 'price', 'costly', 'expensive', 'costs', 'spend', 'spent'],
                'Subscription needed / pricing model': ['subscription', 'monthly fee', 'pay to', 'premium', 'subscription model', 'recurring payment', 'subscribe'],
                'Too slow unlock / few free episodes': ['only free', 'few free', 'slow unlock', 'limited free', 'not enough free', 'unlock slow'],
                'Coin system confusing': ['confusing coins', 'dont understand coins', 'coin system', 'how coins work', 'coins confusing'],
                'Unauthorized charges / billing issues': ['charged without', 'unauthorized', 'auto charge', 'unexpected charge', 'billing issue', 'money taken', 'charged me', 'auto pay']
            },
            'Content Discovery Issues': {
                'Search / discoverability problems': ['cant find', 'search not work', 'hard to find', 'search broken', 'discover', 'find stories'],
                'Poor recommendations / irrelevant suggestions': ['bad recommend', 'irrelevant suggest', 'wrong suggest', 'recommendations suck', 'bad suggestions'],
                'Auto-starts other series': ['auto start', 'starts other', 'switches story', 'changes series', 'jumps to other'],
                'Lack of new content': ['no new content', 'same stories', 'need more content', 'limited content', 'more stories'],
                'Content organization / categories': ['organize', 'categories', 'sort', 'filter', 'organize content']
            },
            'Listening Related Issues': {
                'Crashes / app not working': ['crash', 'not working', 'wont work', 'broken', 'stops working', 'app freeze', 'freezes', 'crashes'],
                'Offline / download issues': ['offline', 'download', 'cant download', 'offline not work', 'download problem'],
                'Buffering / won\'t load': ['buffering', 'wont load', 'loading', 'buffer', 'slow load', 'loads slow'],
                'Playback jumps / episode switching': ['jumps episode', 'skips', 'playback issue', 'episode jump', 'skipping'],
                'Audio quality / sync issues': ['audio quality', 'sound quality', 'sync issue', 'audio sync', 'sound problem'],
                'Notifications / interruptions': ['notification', 'interrupt', 'pause', 'stop playing', 'interruptions']
            },
            'Content Quality Issues': {
                'AI voices / poor narration quality': ['ai voice', 'robot voice', 'artificial voice', 'bad voice', 'voice quality', 'narration', 'narrator', 'robotic', 'computer voice'],
                'Visual vs audio expectation mismatch': ['expected video', 'thought video', 'no video', 'audio only', 'visual expect', 'no pictures'],
                'Story quality / content issues': ['bad story', 'story quality', 'poor content', 'story suck', 'boring story'],
                'Translation / language issues': ['translation', 'language', 'subtitle', 'english', 'translate'],
                'Missing visual content': ['no visual', 'no picture', 'no image', 'audio only', 'no graphics']
            },
            'User Experience Issues': {
                'Interface / navigation problems': ['interface', 'navigation', 'ui', 'user interface', 'hard to use', 'confusing interface'],
                'Login / account issues': ['login', 'account', 'sign in', 'password', 'login problem'],
                'Settings / customization problems': ['settings', 'customize', 'options', 'preferences', 'settings not work'],
                'App performance / speed': ['slow app', 'app slow', 'performance', 'lag', 'sluggish', 'slow'],
                'Update / compatibility issues': ['update', 'version', 'compatibility', 'android version', 'update problem']
            },
            'Support & Service Issues': {
                'Support unresponsive': ['support', 'customer service', 'help', 'contact', 'response', 'unresponsive', 'no response'],
                'Refund / billing disputes': ['refund', 'money back', 'billing', 'charge dispute', 'want refund'],
                'Account recovery problems': ['account recovery', 'lost account', 'cant access', 'recover account'],
                'Feature requests ignored': ['feature request', 'suggestion ignored', 'want feature', 'ignore request'],
                'Communication / transparency': ['communication', 'transparency', 'information', 'explain', 'no communication']
            },
            'Localization Issues': {
                'Missing languages / dubbing': ['language', 'dubbing', 'hindi', 'spanish', 'german', 'french', 'local language', 'other language'],
                'Regional content availability': ['region', 'country', 'available in', 'geographic', 'not available'],
                'Cultural adaptation issues': ['cultural', 'culture', 'local custom', 'cultural content'],
                'Time zone / scheduling problems': ['time zone', 'schedule', 'timing', 'time difference']
            }
        }
        
        for main_category, subcategories in patterns.items():
            for subcategory, keywords in subcategories.items():
                for keyword in keywords:
                    if keyword in review_lower:
                        categories_found.append({
                            'main_category': main_category,
                            'subcategory': subcategory,
                            'keyword_matched': keyword
                        })
                        break  # Only count once per subcategory per review
        
        return categories_found
    
    def analyze_reviews(self):
        """Analyze all reviews and categorize them"""
        print("Categorizing reviews...")
        
        for review in self.reviews_data:
            categories = self.categorize_review(review['text'])
            review['categories'] = categories
            
            # Add to category tracking
            for cat in categories:
                main_cat = cat['main_category']
                sub_cat = cat['subcategory']
                self.categories[main_cat][sub_cat].append({
                    'review': review,
                    'keyword': cat['keyword_matched']
                })
        
        print("Categorization complete!")
        
    def calculate_statistics(self, values):
        """Calculate basic statistics without numpy"""
        if not values:
            return 0, 0
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        std_dev = variance ** 0.5
        return mean, std_dev
        
    def generate_daily_trends(self):
        """Generate day-on-day trend analysis"""
        print("Analyzing daily trends...")
        
        # Group reviews by day and category
        daily_data = defaultdict(lambda: defaultdict(int))
        daily_subcategory_data = defaultdict(lambda: defaultdict(int))
        
        for review in self.reviews_data:
            day = review['day']
            for cat in review['categories']:
                main_cat = cat['main_category']
                sub_cat = cat['subcategory']
                daily_data[day][main_cat] += 1
                daily_subcategory_data[day][f"{main_cat} > {sub_cat}"] += 1
        
        # Calculate trends and anomalies
        trends = {}
        anomalies = []
        
        for main_cat in self.categories.keys():
            daily_counts = []
            days = sorted(daily_data.keys())
            
            for day in days:
                count = daily_data[day][main_cat]
                daily_counts.append(count)
            
            if len(daily_counts) > 3:
                # Calculate rolling average and detect anomalies
                rolling_avg, rolling_std = self.calculate_statistics(daily_counts)
                
                for i, count in enumerate(daily_counts):
                    if rolling_std > 0:
                        z_score = (count - rolling_avg) / rolling_std
                        if z_score > 2.0:  # Significant anomaly
                            anomalies.append({
                                'day': days[i],
                                'category': main_cat,
                                'count': count,
                                'average': rolling_avg,
                                'z_score': z_score,
                                'increase_pct': ((count - rolling_avg) / rolling_avg * 100) if rolling_avg > 0 else 0
                            })
                
                trends[main_cat] = {
                    'daily_counts': daily_counts,
                    'days': days,
                    'average': rolling_avg,
                    'std': rolling_std,
                    'total': sum(daily_counts)
                }
        
        return trends, anomalies, daily_data, daily_subcategory_data
    
    def generate_insights(self, trends, anomalies):
        """Generate product analyst insights"""
        print("Generating insights...")
        
        insights = {
            'total_reviews': len(self.reviews_data),
            'avg_daily_reviews': len(self.reviews_data) / len(set(r['day'] for r in self.reviews_data)) if len(set(r['day'] for r in self.reviews_data)) > 0 else 0,
            'category_summary': {},
            'top_issues': [],
            'trending_up': [],
            'trending_down': [],
            'anomalies': anomalies,
            'recommendations': []
        }
        
        # Category summary
        for main_cat, subcategories in self.categories.items():
            total_issues = sum(len(issues) for issues in subcategories.values())
            insights['category_summary'][main_cat] = {
                'total_count': total_issues,
                'percentage': (total_issues / len(self.reviews_data)) * 100 if len(self.reviews_data) > 0 else 0,
                'subcategories': {}
            }
            
            for sub_cat, issues in subcategories.items():
                if len(issues) > 0:
                    insights['category_summary'][main_cat]['subcategories'][sub_cat] = {
                        'count': len(issues),
                        'percentage_of_category': (len(issues) / total_issues) * 100 if total_issues > 0 else 0
                    }
        
        # Top issues
        all_subcategory_counts = []
        for main_cat, subcategories in self.categories.items():
            for sub_cat, issues in subcategories.items():
                if len(issues) > 0:
                    all_subcategory_counts.append({
                        'main_category': main_cat,
                        'subcategory': sub_cat,
                        'count': len(issues)
                    })
        
        insights['top_issues'] = sorted(all_subcategory_counts, key=lambda x: x['count'], reverse=True)[:10]
        
        # Generate recommendations based on data
        if len(anomalies) > 0:
            insights['recommendations'].append("URGENT: Investigate anomalous spikes detected - potential system issues or external events")
        
        if insights['category_summary']:
            top_category = max(insights['category_summary'].items(), key=lambda x: x[1]['total_count'])
            insights['recommendations'].append(f"HIGH PRIORITY: Address '{top_category[0]}' issues - represents {top_category[1]['percentage']:.1f}% of all complaints")
        
        return insights
    
    def save_results_csv(self, trends, anomalies, daily_data, daily_subcategory_data, insights):
        """Save analysis results to CSV files"""
        print("Saving results...")
        
        import os
        os.makedirs('/workspace/android_analysis_output', exist_ok=True)
        
        # Save parsed reviews
        with open('/workspace/android_analysis_output/android_parsed_reviews.csv', 'w', newline='', encoding='utf-8') as f:
            if self.reviews_data:
                writer = csv.DictWriter(f, fieldnames=['timestamp', 'day', 'reviewer', 'stars', 'text', 'platform'])
                writer.writeheader()
                for review in self.reviews_data:
                    writer.writerow({
                        'timestamp': review['timestamp'],
                        'day': review['day'],
                        'reviewer': review['reviewer'],
                        'stars': review['stars'],
                        'text': review['text'],
                        'platform': review['platform']
                    })
        
        # Save category counts
        with open('/workspace/android_analysis_output/android_category_counts.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['category', 'count', 'percentage'])
            for main_cat, data in insights['category_summary'].items():
                writer.writerow([main_cat, data['total_count'], f"{data['percentage']:.2f}"])
        
        # Save subcategory details
        with open('/workspace/android_analysis_output/android_subcategory_details.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['main_category', 'subcategory', 'count', 'percentage_of_total'])
            for main_cat, subcategories in self.categories.items():
                for sub_cat, issues in subcategories.items():
                    if len(issues) > 0:
                        percentage = (len(issues) / len(self.reviews_data)) * 100 if len(self.reviews_data) > 0 else 0
                        writer.writerow([main_cat, sub_cat, len(issues), f"{percentage:.2f}"])
        
        # Save daily trends
        with open('/workspace/android_analysis_output/android_daily_trends.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['day', 'category', 'count'])
            for day, categories in daily_data.items():
                for category, count in categories.items():
                    writer.writerow([day, category, count])
        
        # Save anomalies
        with open('/workspace/android_analysis_output/android_anomalies.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['day', 'category', 'count', 'average', 'z_score', 'increase_pct'])
            for anomaly in anomalies:
                writer.writerow([
                    anomaly['day'], anomaly['category'], anomaly['count'], 
                    f"{anomaly['average']:.2f}", f"{anomaly['z_score']:.2f}", 
                    f"{anomaly['increase_pct']:.2f}"
                ])
        
        # Save insights as JSON
        with open('/workspace/android_analysis_output/android_insights.json', 'w') as f:
            json.dump(insights, f, indent=2, default=str)
        
        print("Results saved to /workspace/android_analysis_output/")
        return insights

def main():
    analyzer = AndroidReviewAnalyzer('/workspace/App reviews dump - Sheet1.csv')
    
    # Load and parse reviews
    analyzer.load_and_parse_reviews()
    
    # Categorize reviews
    analyzer.analyze_reviews()
    
    # Generate trends and anomalies
    trends, anomalies, daily_data, daily_subcategory_data = analyzer.generate_daily_trends()
    
    # Generate insights
    insights = analyzer.generate_insights(trends, anomalies)
    
    # Save results
    insights = analyzer.save_results_csv(trends, anomalies, daily_data, daily_subcategory_data, insights)
    
    print("\n" + "="*60)
    print("ANDROID REVIEW ANALYSIS COMPLETE")
    print("="*60)
    print(f"Total Android reviews analyzed: {len(analyzer.reviews_data)}")
    print(f"Categories identified: {len(analyzer.categories)}")
    print(f"Anomalies detected: {len(anomalies)}")
    
    if insights['top_issues']:
        print("\nTop 5 Issues:")
        for i, issue in enumerate(insights['top_issues'][:5], 1):
            print(f"{i}. {issue['subcategory']} ({issue['count']} complaints)")
    
    if anomalies:
        print("\nCritical Anomalies Detected:")
        for anomaly in sorted(anomalies, key=lambda x: x['z_score'], reverse=True)[:3]:
            print(f"Day {anomaly['day']}: {anomaly['category']} - {anomaly['count']} complaints (Z-score: {anomaly['z_score']:.2f})")
    
    return insights

if __name__ == "__main__":
    main()