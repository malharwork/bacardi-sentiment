from database import DatabaseManager
from sentiment_analyzer import SentimentAnalyzer
import sqlite3
import time

def analyze_all_posts():
    """Analyze sentiment for all posts without sentiment data"""
    print("Starting sentiment analysis for all unanalyzed posts...")
    
    db = DatabaseManager()
    analyzer = SentimentAnalyzer()
    
    # Get all posts without sentiment analysis directly from database
    conn = sqlite3.connect(db.db_path)
    
    # First, check what columns exist in the table
    cursor = conn.execute("PRAGMA table_info(social_posts)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Available columns: {columns}")
    
    # Check if confidence_score column exists
    has_confidence = 'confidence_score' in columns
    
    query = '''
    SELECT post_id, text, platform, author, timestamp 
    FROM social_posts 
    WHERE sentiment_label IS NULL OR sentiment_score IS NULL
    '''
    
    cursor = conn.execute(query)
    unanalyzed_posts = []
    
    for row in cursor.fetchall():
        unanalyzed_posts.append({
            'post_id': row[0],
            'text': row[1],
            'platform': row[2], 
            'author': row[3],
            'timestamp': row[4]
        })
    
    conn.close()
    
    if not unanalyzed_posts:
        print("✅ All posts already have sentiment analysis!")
        return
    
    print(f"Found {len(unanalyzed_posts)} posts to analyze...")
    
    # Process posts
    conn = sqlite3.connect(db.db_path)
    
    for i, post in enumerate(unanalyzed_posts):
        try:
            # Analyze sentiment
            sentiment = analyzer.analyze_sentiment(post['text'])
            
            # Update post directly in database (with or without confidence_score)
            if has_confidence:
                update_query = '''
                UPDATE social_posts 
                SET sentiment_score = ?, sentiment_label = ?, confidence_score = ?
                WHERE post_id = ?
                '''
                
                conn.execute(update_query, (
                    sentiment.get('sentiment_score', 0),
                    sentiment.get('sentiment_label', 'neutral'),
                    sentiment.get('confidence_score', 0),
                    post['post_id']
                ))
            else:
                update_query = '''
                UPDATE social_posts 
                SET sentiment_score = ?, sentiment_label = ?
                WHERE post_id = ?
                '''
                
                conn.execute(update_query, (
                    sentiment.get('sentiment_score', 0),
                    sentiment.get('sentiment_label', 'neutral'),
                    post['post_id']
                ))
            
            # Progress update every 10 posts
            if (i + 1) % 10 == 0:
                print(f"Progress: {i + 1}/{len(unanalyzed_posts)} posts analyzed")
                conn.commit()  # Save progress
                time.sleep(0.1)  # Small delay
                
        except Exception as e:
            print(f"Error analyzing post {post['post_id']}: {e}")
            print(f"Post text preview: {post['text'][:100]}...")
    
    # Final commit
    conn.commit()
    conn.close()
    
    print("✅ Sentiment analysis complete!")
    
    # Final stats
    conn = sqlite3.connect(db.db_path)
    final_query = '''
    SELECT 
        COUNT(*) as total_posts,
        SUM(CASE WHEN sentiment_label IS NOT NULL THEN 1 ELSE 0 END) as analyzed_posts
    FROM social_posts
    '''
    cursor = conn.execute(final_query)
    result = cursor.fetchone()
    conn.close()
    
    print(f"Final stats: {result[1]} analyzed posts out of {result[0]} total posts")
    
    # Show breakdown by sentiment
    conn = sqlite3.connect(db.db_path)
    breakdown_query = '''
    SELECT 
        sentiment_label,
        COUNT(*) as count
    FROM social_posts 
    WHERE sentiment_label IS NOT NULL
    GROUP BY sentiment_label
    ORDER BY count DESC
    '''
    cursor = conn.execute(breakdown_query)
    print("\nSentiment breakdown:")
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} posts")
    conn.close()

if __name__ == "__main__":
    analyze_all_posts()