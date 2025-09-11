#!/usr/bin/env python3
"""
Script to extract app reviews related to playback and performance issues.
Uses language understanding and pattern matching to identify relevant reviews.
"""

import re
import json
import csv
from typing import List, Dict, Any

def is_playback_performance_issue(text: str) -> bool:
    """
    Determine if a review text relates to playback or performance issues.
    Uses both keyword matching and contextual understanding.
    """
    text_lower = text.lower()
    
    # Crash and freezing issues
    crash_patterns = [
        r'\b(crash|crashing|crashed|freeze|freezing|frozen|hang|hanging|hangs)\b',
        r'\bapp.*stop.*work',
        r'\bstop.*working',
        r'\bnot.*working.*properly',
        r'\bapp.*broken',
        r'\bglitch|glitchy|bug|bugs|buggy'
    ]
    
    # Buffering and loading issues
    buffer_patterns = [
        r'\bbuffer|buffering\b',
        r'\blag|lagging|laggy\b', 
        r'\bslow.*load|loading.*slow\b',
        r'\bload.*forever|loading.*forever\b',
        r'\btakes.*long.*load',
        r'\bload.*turtle',
        r'\bslow.*performance'
    ]
    
    # Audio playback issues
    audio_patterns = [
        r'\baudio.*not.*play',
        r'\bsound.*not.*work',
        r'\bno.*audio|no.*sound',
        r'\bcan\'?t.*hear|cannot.*hear',
        r'\bwon\'?t.*play|can\'?t.*play|doesn\'?t.*play',
        r'\bnot.*playing|stop.*playing',
        r'\bkeeps.*stopping',
        r'\bstop.*every.*\d+.*min',
        r'\baudio.*break|sound.*break',
        r'\bnoise.*much|distort|static',
        r'\bbroken.*speaker',
        r'\bquality.*poor|poor.*quality'
    ]
    
    # Download and offline issues  
    download_patterns = [
        r'\bdownload.*fail|download.*problem|download.*error',
        r'\bwon\'?t.*download|can\'?t.*download',
        r'\bdownload.*not.*work',
        r'\boffline.*not.*work|can\'?t.*play.*offline',
        r'\bdownload.*episode.*not.*play'
    ]
    
    # App functionality issues
    functionality_patterns = [
        r'\bapp.*not.*work|not.*work.*properly',
        r'\bstuck|freeze.*up',
        r'\berror|errors',
        r'\bpause.*not.*work',
        r'\bvolume.*issue|volume.*problem',
        r'\bskip.*episode|jump.*episode',
        r'\breset.*progress|restart.*episode',
        r'\brepeat.*episode|replay.*episode'
    ]
    
    # Performance issues
    performance_patterns = [
        r'\bperformance.*bad|bad.*performance',
        r'\bapp.*slow|slow.*app',
        r'\bhang.*lot|hanging.*much',
        r'\bcrash.*frequent|frequent.*crash',
        r'\bstop.*frequent|frequent.*stop'
    ]
    
    all_patterns = (crash_patterns + buffer_patterns + audio_patterns + 
                   download_patterns + functionality_patterns + performance_patterns)
    
    # Check if any pattern matches
    for pattern in all_patterns:
        if re.search(pattern, text_lower):
            return True
    
    # Additional contextual checks for performance issues
    performance_keywords = [
        'crash', 'freeze', 'hang', 'buffer', 'lag', 'slow', 'loading', 'glitch',
        'bug', 'error', 'broken', 'stuck', 'stop', 'pause', 'skip', 'jump',
        'repeat', 'restart', 'reset', 'download', 'offline', 'audio', 'sound',
        'play', 'playing', 'volume', 'quality', 'noise', 'distort', 'static'
    ]
    
    # Check for negative sentiment with performance keywords
    negative_words = ['not', 'no', 'never', 'can\'t', 'cannot', 'won\'t', 'doesn\'t', 
                     'bad', 'terrible', 'awful', 'horrible', 'worst', 'annoying', 
                     'frustrating', 'disappointed', 'useless']
    
    words = text_lower.split()
    has_performance_keyword = any(keyword in text_lower for keyword in performance_keywords)
    has_negative_sentiment = any(neg in text_lower for neg in negative_words)
    
    return has_performance_keyword and has_negative_sentiment

def parse_reviews_file(filename: str) -> List[Dict[str, Any]]:
    """Parse the reviews file and extract structured review data."""
    reviews = []
    current_review = {}
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        
        # Skip empty lines
        if not line:
            i += 1
            continue
            
        # Check if this is a timestamp line (format: HH:MM)
        if re.match(r'^\d{1,2}:\d{2}$', line):
            # If we have a current review, save it
            if current_review and 'review_text' in current_review:
                reviews.append(current_review.copy())
            current_review = {'timestamp': line}
            i += 1
            continue
        
        # Check if this is an app name line
        if 'Pocket FM: Audio Series (Google Play)' in line:
            current_review['app'] = line
            i += 1
            continue
            
        # Check if this is a rating/reviewer line (contains stars)
        if '★' in line and '·' in line:
            current_review['rating_info'] = line
            # Extract star rating
            star_match = re.search(r'(★+)', line)
            if star_match:
                current_review['stars'] = len(star_match.group(1))
            # Extract reviewer name
            reviewer_match = re.search(r'by\s+([^·]+)', line)
            if reviewer_match:
                current_review['reviewer'] = reviewer_match.group(1).strip()
            i += 1
            continue
            
        # Check if this is a review text (not a system line)
        if (line and not line.startswith('reply |') and 
            not line.startswith('English ·') and not line.startswith('Spanish ·') and
            not line.startswith('German ·') and not line.startswith('French ·') and
            not line.endswith('Google Play') and
            not line.startswith('Appbot:') and
            not line.startswith('----') and
            not line.startswith('English Translation') and
            not re.match(r'^\d+\s+new\s+review', line)):
            
            # This could be review text
            review_text = line
            
            # Check if this spans multiple lines (look ahead)
            j = i + 1
            while j < len(lines) and lines[j].strip():
                next_line = lines[j].strip()
                # Stop if we hit a system line
                if (next_line.startswith('reply |') or 
                    next_line.endswith('Google Play') or
                    next_line.startswith('----') or
                    next_line.startswith('English Translation')):
                    break
                # Add to review text if it's continuation
                if not re.match(r'^\d{1,2}:\d{2}$', next_line) and '★' not in next_line:
                    review_text += ' ' + next_line
                else:
                    break
                j += 1
            
            current_review['review_text'] = review_text
            i = j
            continue
            
        i += 1
    
    # Don't forget the last review
    if current_review and 'review_text' in current_review:
        reviews.append(current_review)
    
    return reviews

def main():
    print("Parsing reviews file...")
    reviews = parse_reviews_file('/workspace/App reviews dump - Sheet1.csv')
    print(f"Total reviews parsed: {len(reviews)}")
    
    # Filter for playback/performance issues
    filtered_reviews = []
    for review in reviews:
        if 'review_text' in review and is_playback_performance_issue(review['review_text']):
            filtered_reviews.append(review)
    
    print(f"Reviews with playback/performance issues: {len(filtered_reviews)}")
    
    # Save as JSON
    with open('/workspace/playback_performance_reviews.json', 'w', encoding='utf-8') as f:
        json.dump(filtered_reviews, f, indent=2, ensure_ascii=False)
    
    # Save as CSV
    if filtered_reviews:
        with open('/workspace/playback_performance_reviews.csv', 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=['timestamp', 'app', 'rating_info', 'stars', 'reviewer', 'review_text'])
            writer.writeheader()
            for review in filtered_reviews:
                writer.writerow(review)
    
    # Print sample results
    print("\nSample filtered reviews:")
    for i, review in enumerate(filtered_reviews[:5]):
        print(f"\n--- Review {i+1} ---")
        print(f"Stars: {review.get('stars', 'N/A')}")
        print(f"Reviewer: {review.get('reviewer', 'N/A')}")
        print(f"Review: {review.get('review_text', 'N/A')[:200]}...")

if __name__ == "__main__":
    main()