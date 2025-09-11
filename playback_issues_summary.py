#!/usr/bin/env python3
"""
Generate a summary analysis of the playback and performance issues found in reviews.
"""

import json
from collections import Counter, defaultdict

def categorize_issue(review_text):
    """Categorize the type of playback/performance issue."""
    text_lower = review_text.lower()
    categories = []
    
    # Crash/Freeze issues
    if any(word in text_lower for word in ['crash', 'crashing', 'crashed', 'freeze', 'freezing', 'frozen', 'hang']):
        categories.append('Crash/Freeze')
    
    # Loading/Buffering issues
    if any(word in text_lower for word in ['buffer', 'buffering', 'loading', 'load', 'slow', 'lag']):
        categories.append('Loading/Buffering')
    
    # Audio playback issues
    if any(phrase in text_lower for phrase in ['audio', 'sound', 'play', 'playing', 'volume', 'hear']):
        if any(neg in text_lower for neg in ['not', 'no', 'can\'t', 'won\'t', 'doesn\'t', 'stop']):
            categories.append('Audio Playback')
    
    # Download issues
    if 'download' in text_lower and any(neg in text_lower for neg in ['not', 'can\'t', 'won\'t', 'fail', 'problem', 'error']):
        categories.append('Download Issues')
    
    # App functionality bugs
    if any(word in text_lower for word in ['bug', 'glitch', 'error', 'broken', 'stuck']):
        categories.append('App Bugs')
    
    # Performance issues
    if any(phrase in text_lower for phrase in ['performance', 'slow', 'hang', 'lag']):
        categories.append('Performance')
    
    return categories if categories else ['General Issues']

def main():
    # Load the filtered reviews
    with open('/workspace/playback_performance_reviews.json', 'r', encoding='utf-8') as f:
        reviews = json.load(f)
    
    print("=== PLAYBACK & PERFORMANCE ISSUES ANALYSIS ===")
    print(f"Total filtered reviews: {len(reviews)}")
    
    # Star rating distribution
    star_counts = Counter(review.get('stars', 0) for review in reviews)
    print(f"\nStar Rating Distribution:")
    for stars in sorted(star_counts.keys()):
        print(f"  {stars} star{'s' if stars != 1 else ''}: {star_counts[stars]} reviews ({star_counts[stars]/len(reviews)*100:.1f}%)")
    
    # Categorize issues
    issue_categories = defaultdict(int)
    for review in reviews:
        categories = categorize_issue(review.get('review_text', ''))
        for category in categories:
            issue_categories[category] += 1
    
    print(f"\nIssue Categories:")
    for category, count in sorted(issue_categories.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count} reviews")
    
    # Most common keywords
    all_text = ' '.join(review.get('review_text', '').lower() for review in reviews)
    words = all_text.split()
    
    # Filter for relevant performance keywords
    performance_keywords = ['crash', 'freeze', 'hang', 'buffer', 'lag', 'slow', 'loading', 
                           'glitch', 'bug', 'error', 'broken', 'stuck', 'stop', 'download',
                           'audio', 'sound', 'play', 'not', 'can\'t', 'won\'t', 'doesn\'t']
    
    keyword_counts = Counter(word for word in words if word in performance_keywords)
    
    print(f"\nMost Common Performance Keywords:")
    for keyword, count in keyword_counts.most_common(15):
        print(f"  '{keyword}': {count} occurrences")
    
    # Sample severe issues (1-star reviews)
    severe_issues = [r for r in reviews if r.get('stars') == 1]
    print(f"\nSample Severe Issues (1-star reviews): {len(severe_issues)} total")
    
    for i, review in enumerate(severe_issues[:10]):
        print(f"\n{i+1}. Reviewer: {review.get('reviewer', 'N/A')}")
        print(f"   Issue: {review.get('review_text', 'N/A')[:150]}...")

if __name__ == "__main__":
    main()