import asyncio
import asyncpraw
import aiohttp
import sqlite3
from datetime import datetime, timedelta
import time
import random
import config
from database import DatabaseManager

class AsyncDataCollector:
    def __init__(self):
        self.db = DatabaseManager()
        
        # Initialize Async Reddit API
        self.reddit = None
        try:
            self.reddit = asyncpraw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent="BacardiSentimentBot/1.0"
            )
            print("✅ Async Reddit API initialized successfully")
        except Exception as e:
            print(f"❌ Async Reddit API initialization failed: {e}")
        
        # YouTube API setup
        self.youtube_api_key = getattr(config, 'YOUTUBE_API_KEY', None)
        if self.youtube_api_key:
            print("✅ YouTube API key found")
        else:
            print("⚠️ YouTube API key not configured")
    
    async def collect_reddit_posts_async(self, keyword, limit=100):
        """Async Reddit post collection"""
        if not self.reddit:
            print("❌ Reddit API not available")
            return []
        
        posts = []
        print(f"🔍 Async searching Reddit for: '{keyword}'")
        
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
                    subreddit = await self.reddit.subreddit(subreddit_name)
                    
                    # Search within subreddit
                    async for submission in subreddit.search(keyword, limit=20, time_filter='year'):
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
                            await submission.comments.replace_more(limit=0)
                            comment_count = 0
                            async for comment in submission.comments:
                                if hasattr(comment, 'body') and len(comment.body) > 20 and comment_count < 5:
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
                                    comment_count += 1
                        except:
                            pass  # Skip comment collection if it fails
                        
                        if len(posts) >= limit:
                            break
                    
                    await asyncio.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    print(f"⚠️ Error searching r/{subreddit_name}: {e}")
                    continue
                
                if len(posts) >= limit:
                    break
            
            # Also search all of Reddit
            try:
                all_subreddit = await self.reddit.subreddit('all')
                async for submission in all_subreddit.search(keyword, limit=30, time_filter='year'):
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
    
    async def collect_youtube_comments_async(self, keyword, limit=100):
        """Async YouTube comment collection"""
        if not self.youtube_api_key:
            print("❌ YouTube API key not configured")
            return []
        
        comments = []
        print(f"🔍 Async searching YouTube for: '{keyword}'")
        
        try:
            async with aiohttp.ClientSession() as session:
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
                
                async with session.get(search_url, params=search_params) as response:
                    if response.status != 200:
                        print(f"❌ YouTube search failed: {response.status}")
                        return []
                    
                    search_data = await response.json()
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
                            
                            async with session.get(comments_url, params=comments_params) as comments_response:
                                if comments_response.status != 200:
                                    continue
                                
                                comments_data = await comments_response.json()
                                
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
                            
                            await asyncio.sleep(0.5)  # Rate limiting
                            
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
        return self.db.save_post(post_data)
    
    async def collect_api_data_async(self, keywords=None, limit_per_keyword=100):
        """Async API data collection"""
        if keywords is None:
            keywords = getattr(config, 'BRAND_KEYWORDS', ['bacardi', 'breezer'])
        
        all_posts = []
        
        print("📡 Starting Async API Data Collection")
        print("=" * 40)
        
        try:
            for keyword in keywords:
                print(f"\n🎯 Processing keyword: {keyword}")
                
                # Collect Reddit data
                reddit_posts = await self.collect_reddit_posts_async(keyword, limit_per_keyword//2)
                if reddit_posts:
                    all_posts.extend(reddit_posts)
                    print(f"  📊 Reddit: {len(reddit_posts)} posts")
                
                # Collect YouTube data
                youtube_posts = await self.collect_youtube_comments_async(keyword, limit_per_keyword//2)
                if youtube_posts:
                    all_posts.extend(youtube_posts)
                    print(f"  📺 YouTube: {len(youtube_posts)} comments")
                
                # Small delay between keywords
                await asyncio.sleep(2)
            
            print(f"\n✅ API collection complete: {len(all_posts)} posts")
            
            # Save posts to database
            saved_count = 0
            for post in all_posts:
                try:
                    if self.save_post(post):
                        saved_count += 1
                except Exception as e:
                    print(f"Error saving post: {e}")
                    continue
            
            print(f"💾 Saved {saved_count} posts to database")
            
        finally:
            # Close Reddit connection
            if self.reddit:
                await self.reddit.close()
        
        return all_posts

async def main():
    """Main async function"""
    print("🚀 Async Bacardi Data Collector")
    print("📡 Using AsyncPRAW and aiohttp")
    print("=" * 40)
    
    collector = AsyncDataCollector()
    
    # Collection options
    print("\n📋 Collection Options:")
    print("1. Standard API Collection (Reddit + YouTube)")
    print("2. Custom Keywords")
    print("3. Quick Test")
    
    choice = input("\nSelect option (1-3): ").strip()
    
    if choice == "1":
        # Standard collection
        keywords = ['bacardi', 'breezer', 'captain morgan', 'malibu']
        print(f"\n🎯 Standard Collection")
        print(f"📊 Keywords: {', '.join(keywords)}")
        
        confirm = input("Proceed? (y/n): ").lower().strip()
        if confirm == 'y':
            await collector.collect_api_data_async(keywords)
    
    elif choice == "2":
        # Custom keywords
        custom_input = input("Enter keywords (comma-separated): ").strip()
        if custom_input:
            custom_keywords = [k.strip() for k in custom_input.split(',')]
            print(f"📊 Using keywords: {', '.join(custom_keywords)}")
            await collector.collect_api_data_async(custom_keywords)
        else:
            print("❌ No keywords provided")
    
    elif choice == "3":
        # Quick test
        test_keywords = ['bacardi']
        print(f"\n⚡ Quick Test")
        print(f"📊 Testing with: {', '.join(test_keywords)}")
        await collector.collect_api_data_async(test_keywords, limit_per_keyword=20)
    
    else:
        print("❌ Invalid choice. Exiting.")
        return
    
    print(f"\n🎯 Next Steps:")
    print(f"1. Run sentiment analysis: python analyze_sentiment.py")
    print(f"2. Launch dashboard: streamlit run dashboard.py")

if __name__ == "__main__":
    asyncio.run(main())