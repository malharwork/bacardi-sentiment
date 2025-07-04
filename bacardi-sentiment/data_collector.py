import praw
import requests
import sqlite3
from datetime import datetime, timedelta
import time
import random
import config  
from database import DatabaseManager

class EnhancedDataCollector:
    def __init__(self):
        self.db = DatabaseManager()
        try:
            self.reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent="BacardiSentimentBot/1.0"
            )
            print("✅ Reddit API initialized successfully")
        except Exception as e:
            print(f"❌ Reddit API initialization failed: {e}")
            self.reddit = None
        
        # YouTube API setup
        self.youtube_api_key = getattr(config, 'YOUTUBE_API_KEY', None)
        if self.youtube_api_key:
            print("✅ YouTube API key found")
        else:
            print("⚠️ YouTube API key not configured")
    
    def collect_reddit_posts(self, keyword, limit=100):
        """Collect Reddit posts with enhanced search"""
        if not self.reddit:
            print("❌ Reddit API not available")
            return []
        
        posts = []
        print(f"🔍 Searching Reddit for: '{keyword}'")
        
        try:
            # Search across multiple subreddits
            subreddits_to_search = [
                'alcohol', 'rum', 'cocktails', 'bartenders', 'mixology', 
                'drinks', 'liquor', 'spirits', 'party', 'nightlife',
                'reviews', 'ProductReviews', 'BuyItForLife'
            ]
            
            # Search specific subreddits
            for subreddit_name in subreddits_to_search[:5]:  # Limit to avoid rate limits
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Search within subreddit
                    for submission in subreddit.search(keyword, limit=20, time_filter='year'):
                        # Skip if already processed
                        if any(p.get('post_id') == submission.id for p in posts):
                            continue
                        
                        post_data = {
                            'post_id': submission.id,
                            'platform': 'reddit',
                            'text': f"{submission.title} {submission.selftext}".strip(),
                            'author': str(submission.author) if submission.author else 'deleted',
                            'timestamp': datetime.fromtimestamp(submission.created_utc).isoformat(),
                            'subreddit': subreddit_name,
                            'upvotes': submission.score,
                            'comments': submission.num_comments,
                            'url': f"https://reddit.com{submission.permalink}",
                            'keyword_matched': keyword.lower(),
                            'brand_category': self.categorize_brand(keyword)
                        }
                        
                        if len(post_data['text']) > 10:  # Skip very short posts
                            posts.append(post_data)
                        
                        # Collect top comments
                        try:
                            submission.comments.replace_more(limit=0)
                            for comment in submission.comments.list()[:5]:  # Top 5 comments
                                if hasattr(comment, 'body') and len(comment.body) > 20:
                                    comment_data = {
                                        'post_id': f"{submission.id}_{comment.id}",
                                        'platform': 'reddit',
                                        'text': comment.body,
                                        'author': str(comment.author) if comment.author else 'deleted',
                                        'timestamp': datetime.fromtimestamp(comment.created_utc).isoformat(),
                                        'subreddit': subreddit_name,
                                        'upvotes': comment.score,
                                        'comments': 0,
                                        'url': f"https://reddit.com{submission.permalink}",
                                        'keyword_matched': keyword.lower(),
                                        'brand_category': self.categorize_brand(keyword)
                                    }
                                    posts.append(comment_data)
                        except:
                            pass  # Skip comment collection if it fails
                        
                        if len(posts) >= limit:
                            break
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    print(f"⚠️ Error searching r/{subreddit_name}: {e}")
                    continue
                
                if len(posts) >= limit:
                    break
            
            # Also search all of Reddit
            try:
                for submission in self.reddit.subreddit('all').search(keyword, limit=30, time_filter='year'):
                    if any(p.get('post_id') == submission.id for p in posts):
                        continue
                    
                    post_data = {
                        'post_id': submission.id,
                        'platform': 'reddit',
                        'text': f"{submission.title} {submission.selftext}".strip(),
                        'author': str(submission.author) if submission.author else 'deleted',
                        'timestamp': datetime.fromtimestamp(submission.created_utc).isoformat(),
                        'subreddit': submission.subreddit.display_name,
                        'upvotes': submission.score,
                        'comments': submission.num_comments,
                        'url': f"https://reddit.com{submission.permalink}",
                        'keyword_matched': keyword.lower(),
                        'brand_category': self.categorize_brand(keyword)
                    }
                    
                    if len(post_data['text']) > 10:
                        posts.append(post_data)
                    
                    if len(posts) >= limit:
                        break
                        
            except Exception as e:
                print(f"⚠️ Error searching all of Reddit: {e}")
            
            print(f"✅ Collected {len(posts)} Reddit posts/comments for '{keyword}'")
            return posts
            
        except Exception as e:
            print(f"❌ Reddit collection error for '{keyword}': {e}")
            return []
    
    def collect_youtube_comments(self, keyword, limit=100):
        """Collect YouTube comments with enhanced search"""
        if not self.youtube_api_key:
            print("❌ YouTube API key not configured")
            return []
        
        comments = []
        print(f"🔍 Searching YouTube for: '{keyword}'")
        
        try:
            # Search for videos
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                'part': 'snippet',
                'q': f"{keyword} review taste alcohol rum",
                'type': 'video',
                'maxResults': 20,
                'key': self.youtube_api_key,
                'order': 'relevance',
                'publishedAfter': (datetime.now() - timedelta(days=365)).isoformat() + 'Z'
            }
            
            search_response = requests.get(search_url, params=search_params)
            if search_response.status_code != 200:
                print(f"❌ YouTube search failed: {search_response.status_code}")
                return []
            
            search_data = search_response.json()
            video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
            
            if not video_ids:
                print(f"⚠️ No YouTube videos found for '{keyword}'")
                return []
            
            # Get comments for each video
            for video_id in video_ids[:10]:  # Limit to first 10 videos
                try:
                    comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
                    comments_params = {
                        'part': 'snippet',
                        'videoId': video_id,
                        'maxResults': 50,
                        'key': self.youtube_api_key,
                        'order': 'relevance'
                    }
                    
                    comments_response = requests.get(comments_url, params=comments_params)
                    if comments_response.status_code != 200:
                        continue
                    
                    comments_data = comments_response.json()
                    
                    for item in comments_data.get('items', []):
                        comment_snippet = item['snippet']['topLevelComment']['snippet']
                        comment_text = comment_snippet['textDisplay']
                        
                        # Only collect relevant comments
                        if any(term.lower() in comment_text.lower() for term in [keyword, 'taste', 'flavor', 'drink', 'good', 'bad']):
                            comment_data = {
                                'post_id': item['id'],
                                'platform': 'youtube',
                                'text': comment_text,
                                'author': comment_snippet['authorDisplayName'],
                                'timestamp': comment_snippet['publishedAt'],
                                'video_id': video_id,
                                'likes': comment_snippet.get('likeCount', 0),
                                'comments': item['snippet'].get('totalReplyCount', 0),
                                'url': f"https://youtube.com/watch?v={video_id}",
                                'keyword_matched': keyword.lower(),
                                'brand_category': self.categorize_brand(keyword)
                            }
                            
                            if len(comment_text) > 15:  # Skip very short comments
                                comments.append(comment_data)
                        
                        if len(comments) >= limit:
                            break
                    
                    time.sleep(0.5)  # Rate limiting
                    
                except Exception as e:
                    print(f"⚠️ Error getting comments for video {video_id}: {e}")
                    continue
                
                if len(comments) >= limit:
                    break
            
            print(f"✅ Collected {len(comments)} YouTube comments for '{keyword}'")
            return comments
            
        except Exception as e:
            print(f"❌ YouTube collection error for '{keyword}': {e}")
            return []
    
    def categorize_brand(self, keyword):
        """Categorize brand for competitive analysis"""
        keyword_lower = keyword.lower()
        
        # Primary brand
        if keyword_lower in ['bacardi']:
            return 'primary'
        
        # Premium competitors
        premium_brands = ['grey goose', 'hennessy', 'johnnie walker', 'chivas regal', 'macallan']
        if any(brand in keyword_lower for brand in premium_brands):
            return 'premium_competitor'
        
        # Direct competitors (rum/vodka)
        direct_competitors = ['captain morgan', 'malibu', 'absolut', 'smirnoff', 'jose cuervo']
        if any(brand in keyword_lower for brand in direct_competitors):
            return 'direct_competitor'
        
        # Budget competitors
        budget_brands = ['svedka', 'burnetts', 'new amsterdam', 'pinnacle']
        if any(brand in keyword_lower for brand in budget_brands):
            return 'budget_competitor'
        
        return 'other'
    
    def save_post(self, post_data):
        """Save a single post to database"""
        conn = sqlite3.connect(self.db.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR IGNORE INTO social_posts 
                (platform, post_id, text, author, timestamp, likes, 
                 comments, upvotes, url, keyword_matched, brand_category, subreddit, video_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data.get('platform'),
                post_data.get('post_id'),
                post_data.get('text'),
                post_data.get('author'),
                post_data.get('timestamp'),
                post_data.get('likes', 0),
                post_data.get('comments', 0),
                post_data.get('upvotes', 0),
                post_data.get('url'),
                post_data.get('keyword_matched'),
                post_data.get('brand_category'),
                post_data.get('subreddit'),
                post_data.get('video_id')
            ))
            
            conn.commit()
            return cursor.rowcount > 0
            
        except Exception as e:
            print(f"Error saving post: {e}")
            return False
        finally:
            conn.close()
    
    def collect_competitor_data(self):
        """Collect data for all competitors defined in config"""
        print("🏆 Starting Comprehensive Competitor Analysis")
        print("=" * 50)
        
        # Get competitor brands from config
        competitor_brands = []
        
        # Add primary brand
        competitor_brands.append('bacardi')
        
        # Add competitors from config if they exist
        if hasattr(config, 'COMPETITORS'):
            competitor_brands.extend(config.COMPETITORS)
        else:
            # Default competitor list
            competitor_brands.extend([
                'captain morgan', 'malibu', 'absolut vodka', 'smirnoff', 
                'grey goose', 'hennessy', 'jose cuervo', 'johnnie walker'
            ])
        
        all_posts = []
        
        for brand in competitor_brands:
            print(f"\n🎯 Analyzing: {brand.title()}")
            print("-" * 30)
            
            brand_posts = []
            
            # Collect Reddit data
            reddit_posts = self.collect_reddit_posts(brand, limit=50)
            if reddit_posts:
                brand_posts.extend(reddit_posts)
                print(f"  📊 Reddit: {len(reddit_posts)} posts")
            
            # Collect YouTube data
            youtube_posts = self.collect_youtube_comments(brand, limit=50)
            if youtube_posts:
                brand_posts.extend(youtube_posts)
                print(f"  📺 YouTube: {len(youtube_posts)} comments")
            
            # Save to database
            if brand_posts:
                saved_count = 0
                for post in brand_posts:
                    try:
                        if self.save_post(post):
                            saved_count += 1
                    except Exception as e:
                        print(f"⚠️ Error saving post: {e}")
                        continue
                
                print(f"  💾 Saved: {saved_count} posts to database")
                all_posts.extend(brand_posts)
            else:
                print(f"  ⚠️ No data collected for {brand}")
            
            # Rate limiting between brands
            time.sleep(2)
        
        print(f"\n🎉 Competitor Analysis Complete!")
        print(f"📊 Total posts collected: {len(all_posts)}")
        print(f"🏢 Brands analyzed: {len(competitor_brands)}")
        
        # Generate summary report
        self.generate_competitor_summary(competitor_brands)
        
        return all_posts
    
    def generate_competitor_summary(self, brands):
        """Generate a summary of competitor data collection"""
        print(f"\n📋 COMPETITOR ANALYSIS SUMMARY")
        print("=" * 40)
        
        try:
            conn = sqlite3.connect(self.db.db_path)
            
            for brand in brands:
                query = '''
                SELECT 
                    COUNT(*) as total_posts,
                    COUNT(DISTINCT platform) as platforms,
                    AVG(CASE WHEN platform = 'reddit' THEN upvotes ELSE likes END) as avg_engagement,
                    MIN(timestamp) as earliest_post,
                    MAX(timestamp) as latest_post
                FROM social_posts 
                WHERE LOWER(keyword_matched) = LOWER(?)
                '''
                
                cursor = conn.execute(query, (brand,))
                result = cursor.fetchone()
                
                if result and result[0] > 0:
                    print(f"\n🎯 {brand.title()}:")
                    print(f"   📊 Posts: {result[0]}")
                    print(f"   🌐 Platforms: {result[1]}")
                    print(f"   👍 Avg Engagement: {result[2]:.1f}" if result[2] else "   👍 Avg Engagement: N/A")
                    print(f"   📅 Date Range: {result[3][:10] if result[3] else 'N/A'} to {result[4][:10] if result[4] else 'N/A'}")
            
            # Overall summary
            summary_query = '''
            SELECT 
                brand_category,
                COUNT(*) as posts,
                COUNT(DISTINCT keyword_matched) as brands
            FROM social_posts 
            WHERE brand_category IS NOT NULL
            GROUP BY brand_category
            ORDER BY posts DESC
            '''
            
            cursor = conn.execute(summary_query)
            results = cursor.fetchall()
            
            if results:
                print(f"\n📈 CATEGORY BREAKDOWN:")
                for row in results:
                    print(f"   {row[0].title().replace('_', ' ')}: {row[1]} posts ({row[2]} brands)")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error generating summary: {e}")
        
        print(f"\n✅ Data collection complete!")
        print(f"💡 Run sentiment analysis: python analyze_sentiment.py")
        print(f"📊 View dashboard: streamlit run dashboard.py")
    
    def collect_historical_data(self, days_back=365):
        """Collect historical data for comprehensive analysis"""
        print(f"📅 Collecting Historical Data ({days_back} days)")
        print("=" * 50)
        
        # Collect competitor data
        all_posts = self.collect_competitor_data()
        
        # Additional targeted searches
        targeted_keywords = [
            'rum review', 'vodka comparison', 'best rum brand', 
            'alcohol taste test', 'cocktail recommendations'
        ]
        
        print(f"\n🎯 Collecting Targeted Content")
        print("-" * 30)
        
        for keyword in targeted_keywords:
            print(f"\n🔍 Searching: '{keyword}'")
            
            # Reddit search
            reddit_posts = self.collect_reddit_posts(keyword, limit=25)
            if reddit_posts:
                for post in reddit_posts:
                    post['keyword_matched'] = keyword
                    post['brand_category'] = 'general'
                    try:
                        self.save_post(post)
                    except:
                        pass
                print(f"  📊 Reddit: {len(reddit_posts)} posts")
            
            # YouTube search
            youtube_posts = self.collect_youtube_comments(keyword, limit=25)
            if youtube_posts:
                for post in youtube_posts:
                    post['keyword_matched'] = keyword
                    post['brand_category'] = 'general'
                    try:
                        self.save_post(post)
                    except:
                        pass
                print(f"  📺 YouTube: {len(youtube_posts)} comments")
            
            all_posts.extend(reddit_posts)
            all_posts.extend(youtube_posts)
            
            time.sleep(1)  # Rate limiting
        
        print(f"\n🎉 Historical Data Collection Complete!")
        print(f"📊 Total posts collected: {len(all_posts)}")
        
        return all_posts

def main():
    """Main execution function"""
    print("🚀 Enhanced Bacardi Sentiment Analysis Data Collector")
    print("🏆 With Comprehensive Competitor Analysis")
    print("=" * 60)
    
    collector = EnhancedDataCollector()
    
    # Choose collection type
    print("\n📋 Collection Options:")
    print("1. Full Competitor Analysis (Recommended)")
    print("2. Historical Data Collection (365 days)")
    print("3. Quick Bacardi-only Collection")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        # Full competitor analysis
        collector.collect_competitor_data()
    elif choice == "2":
        # Historical data collection
        collector.collect_historical_data()
    elif choice == "3":
        # Quick Bacardi collection
        print("\n🎯 Quick Bacardi Collection")
        all_posts = []
        
        reddit_posts = collector.collect_reddit_posts('bacardi', limit=100)
        youtube_posts = collector.collect_youtube_comments('bacardi', limit=100)
        
        all_posts.extend(reddit_posts)
        all_posts.extend(youtube_posts)
        
        # Save posts
        saved_count = 0
        for post in all_posts:
            try:
                if collector.save_post(post):
                    saved_count += 1
            except:
                pass
        
        print(f"\n✅ Collected and saved {saved_count} posts")
    else:
        print("❌ Invalid choice. Exiting.")
        return
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Run sentiment analysis: python analyze_sentiment.py")
    print(f"2. View dashboard: streamlit run dashboard.py")
    print(f"3. Check database: {collector.db.db_path}")

if __name__ == "__main__":
    main()