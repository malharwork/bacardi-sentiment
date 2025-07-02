import sqlite3
import pandas as pd
from datetime import datetime
import os

class DatabaseManager:
    def __init__(self, db_path="data/bacardi_posts.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.init_database()
    
    def init_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                post_id TEXT UNIQUE,
                text TEXT NOT NULL,
                author TEXT,
                timestamp DATETIME,
                sentiment_score REAL,
                sentiment_label TEXT,
                confidence REAL,
                engagement_score REAL,
                likes INTEGER DEFAULT 0,
                retweets INTEGER DEFAULT 0,
                comments INTEGER DEFAULT 0,
                followers INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Daily summary table for trends
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS daily_summary (
                date DATE PRIMARY KEY,
                total_posts INTEGER,
                positive_count INTEGER,
                negative_count INTEGER,
                neutral_count INTEGER,
                avg_sentiment REAL,
                top_keywords TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Keywords tracking table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS keyword_mentions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT,
                post_id TEXT,
                platform TEXT,
                timestamp DATETIME,
                sentiment_score REAL,
                FOREIGN KEY (post_id) REFERENCES social_posts (post_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"Database initialized at: {self.db_path}")
    
    def save_posts(self, posts_data):
        """Save analyzed posts to database"""
        if not posts_data:
            print("No posts to save")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        saved_count = 0
        skipped_count = 0
        
        for post in posts_data:
            try:
                # Calculate engagement score based on platform
                engagement_score = self._calculate_engagement_score(post)
                
                cursor.execute('''
                    INSERT OR IGNORE INTO social_posts 
                    (platform, post_id, text, author, timestamp, sentiment_score, 
                     sentiment_label, confidence, engagement_score, likes, retweets, 
                     comments, followers)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post.get('platform'),
                    post.get('post_id'),
                    post.get('text'),
                    post.get('author'),
                    post.get('timestamp'),
                    post.get('sentiment_score'),
                    post.get('sentiment_label'),
                    post.get('confidence'),
                    engagement_score,
                    post.get('likes', 0),
                    post.get('retweets', 0),
                    post.get('comments', 0),
                    post.get('followers', 0)
                ))
                
                if cursor.rowcount > 0:
                    saved_count += 1
                else:
                    skipped_count += 1
                    
            except sqlite3.IntegrityError:
                skipped_count += 1
                continue
        
        conn.commit()
        conn.close()
        
        print(f"Saved {saved_count} new posts, skipped {skipped_count} duplicates")
        return saved_count
    
    def _calculate_engagement_score(self, post):
        """Calculate simple engagement score based on platform metrics"""
        if post.get('platform') == 'twitter':
            likes = post.get('likes', 0)
            retweets = post.get('retweets', 0)
            followers = max(post.get('followers', 1), 1)  # Avoid division by zero
            return (likes + retweets * 2) / followers * 100
        
        elif post.get('platform') == 'reddit':
            upvotes = post.get('upvotes', 0)
            comments = post.get('comments', 0)
            return upvotes + comments * 2
        
        return 0
    
    def get_sentiment_trends(self, days=7):
        """Get sentiment trends for last N days"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT DATE(timestamp) as date,
                   AVG(sentiment_score) as avg_sentiment,
                   COUNT(*) as post_count,
                   SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive,
                   SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative,
                   SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral,
                   AVG(engagement_score) as avg_engagement
            FROM social_posts 
            WHERE timestamp >= date('now', '-{} days')
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        '''.format(days)
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_platform_breakdown(self):
        """Get sentiment breakdown by platform"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT platform,
                   COUNT(*) as total_posts,
                   AVG(sentiment_score) as avg_sentiment,
                   SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive,
                   SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative,
                   SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral
            FROM social_posts 
            WHERE timestamp >= date('now', '-7 days')
            GROUP BY platform
        '''
        
        df = pd.read_sql_query(query, conn)
        conn.close()
        return df
    
    def get_recent_posts(self, limit=10):
        """Get most recent posts"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT platform, text, sentiment_label, sentiment_score, 
                   timestamp, author, likes, retweets, comments
            FROM social_posts 
            ORDER BY timestamp DESC 
            LIMIT ?
        '''
        
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df
    
    def get_top_negative_posts(self, limit=5):
        """Get most negative posts for alerts"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
            SELECT platform, text, sentiment_score, author, timestamp
            FROM social_posts 
            WHERE sentiment_label = 'negative' 
            AND timestamp >= date('now', '-1 days')
            ORDER BY sentiment_score ASC 
            LIMIT ?
        '''
        
        df = pd.read_sql_query(query, conn, params=[limit])
        conn.close()
        return df
    
    def get_database_stats(self):
        """Get overall database statistics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total posts
        cursor.execute("SELECT COUNT(*) FROM social_posts")
        total_posts = cursor.fetchone()[0]
        
        # Posts by sentiment
        cursor.execute('''
            SELECT sentiment_label, COUNT(*) 
            FROM social_posts 
            GROUP BY sentiment_label
        ''')
        sentiment_breakdown = dict(cursor.fetchall())
        
        # Date range
        cursor.execute('''
            SELECT MIN(timestamp), MAX(timestamp) 
            FROM social_posts
        ''')
        date_range = cursor.fetchone()
        
        # Platform breakdown
        cursor.execute('''
            SELECT platform, COUNT(*) 
            FROM social_posts 
            GROUP BY platform
        ''')
        platform_breakdown = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            'total_posts': total_posts,
            'sentiment_breakdown': sentiment_breakdown,
            'date_range': date_range,
            'platform_breakdown': platform_breakdown
        }

    def get_unanalyzed_posts(self):
        """Get all posts without sentiment analysis"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        SELECT post_id, text, platform, author, timestamp 
        FROM social_posts 
        WHERE sentiment_label IS NULL OR sentiment_score IS NULL
        '''
        
        posts = []
        cursor = conn.execute(query)
        
        for row in cursor.fetchall():
            posts.append({
                'post_id': row[0],
                'text': row[1],
                'platform': row[2], 
                'author': row[3],
                'timestamp': row[4]
            })
        
        conn.close()
        return posts

    def update_post_sentiment(self, post_id, sentiment_data):
        """Update sentiment for a specific post"""
        conn = sqlite3.connect(self.db_path)
        
        query = '''
        UPDATE social_posts 
        SET sentiment_score = ?, sentiment_label = ?, confidence_score = ?
        WHERE post_id = ?
        '''
        
        conn.execute(query, (
            sentiment_data.get('sentiment_score', 0),
            sentiment_data.get('sentiment_label', 'neutral'),
            sentiment_data.get('confidence_score', 0),
            post_id
        ))
        
        conn.commit()
        conn.close()
    
    def clear_database(self):
        """Clear all data from database (use with caution!)"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM social_posts")
        cursor.execute("DELETE FROM daily_summary")
        cursor.execute("DELETE FROM keyword_mentions")
        
        conn.commit()
        conn.close()
        print("Database cleared!")
    
    def backup_database(self, backup_path=None):
        """Create a backup of the database"""
        if backup_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"data/bacardi_posts_backup_{timestamp}.db"
        
        # Simple file copy for SQLite
        import shutil
        shutil.copy2(self.db_path, backup_path)
        print(f"Database backed up to: {backup_path}")
        return backup_path


if __name__ == "__main__":
    # Initialize database without test data
    db = DatabaseManager()
    
    print("\nDatabase setup complete!")
    print(f"Database file created at: {db.db_path}")
    
    # Show current stats
    stats = db.get_database_stats()
    print(f"Current posts in database: {stats['total_posts']}")
    
    print("\nYou can now run the data collector to add real social media data.")