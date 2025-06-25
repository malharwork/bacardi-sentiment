import praw
import requests
from datetime import datetime, timedelta
import time
import re
import json
from urllib.parse import quote

try:
    from config_local import *
    print("✅ Config loaded from config_local.py")
except ImportError:
    print("❌ config_local.py not found - using fallback")
    REDDIT_CLIENT_ID = "aAwa29mpNMRzQKtgkfebQw"
    REDDIT_CLIENT_SECRET = "TMPXj33kr77IsgGDnoWL1rADnCRAAw"
    REDDIT_USERNAME = "Low-Iron-2783"
    REDDIT_PASSWORD = "uZD2.aBXFsb)B=/"
    
    # API credentials for platforms
    YOUTUBE_API_KEY = "AIzaSyDX43Noo2pNguffliKNtCamVMdvscEiiCs"
    FACEBOOK_ACCESS_TOKEN = "EACEdBhRweVMBO5OipxlZA9q7KE8uzze0SCZAqkU6n1mlQZA6XKYaJuS6ZBHzIoKCfrtwbfL8E5AFGQvNFqCRKgbLwhZAGOqut1EpU6ZAKXRERwJqH6HTHcGSyQ40agmRO9ZBVOVkfr9FOZCNaZBU3tCLDqhnaL1ZA3h3QFZAt2Qt4XHYWLAZAv6MS7wp5ZBUIhzvpeJMWFRbXXjPrFTOiySkbiQBuXv6xoXtvZAMx5E9v47P0fMUbkYpwZD"
    INSTAGRAM_ACCESS_TOKEN = "your_instagram_access_token"
# Brand keywords
BRAND_KEYWORDS = [
    'bacardi', 
    'breezer', 
    'bacardi rum', 
    'white rum bacardi',
    'bacardi superior', 
    'bacardi gold'
]

class SocialMediaCollector:
    def __init__(self):
        self.setup_apis()
        print("Social Media Collector initialized")
    
    def setup_apis(self):
        """Initialize API connections"""
        # Reddit API setup
        try:
            if not REDDIT_CLIENT_ID or REDDIT_CLIENT_ID == "your_reddit_client_id":
                print("⚠️ Reddit credentials not configured")
                self.reddit = None
            else:
                self.reddit = praw.Reddit(
                    client_id=REDDIT_CLIENT_ID,
                    client_secret=REDDIT_CLIENT_SECRET,
                    username=REDDIT_USERNAME,
                    password=REDDIT_PASSWORD,
                    user_agent="BacardiSentimentPOC/1.0"
                )
                
                # Test Reddit connection
                user = self.reddit.user.me()
                print(f"✅ Reddit API connected as: {user}")
                
        except Exception as e:
            print(f"❌ Reddit API setup failed: {e}")
            self.reddit = None
            
        # YouTube API setup
        try:
            if not YOUTUBE_API_KEY or YOUTUBE_API_KEY == "your_youtube_api_key_here":
                print("⚠️ YouTube API key not configured")
                self.youtube_available = False
            else:
                self.youtube_available = True
                print("✅ YouTube API configured")
                
        except Exception as e:
            print(f"❌ YouTube API setup failed: {e}")
            self.youtube_available = False
            
        # Facebook API setup
        try:
            if not FACEBOOK_ACCESS_TOKEN or FACEBOOK_ACCESS_TOKEN == "your_facebook_access_token_here":
                print("⚠️ Facebook access token not configured")
                self.facebook_available = False
            else:
                self.facebook_available = True
                print("✅ Facebook API configured")
                
        except Exception as e:
            print(f"❌ Facebook API setup failed: {e}")
            self.facebook_available = False
            
        # Instagram API setup
        try:
            if not INSTAGRAM_ACCESS_TOKEN or INSTAGRAM_ACCESS_TOKEN == "your_instagram_access_token_here":
                print("⚠️ Instagram access token not configured")
                self.instagram_available = False
            else:
                self.instagram_available = True
                print("✅ Instagram API configured")
                
        except Exception as e:
            print(f"❌ Instagram API setup failed: {e}")
            self.instagram_available = False
    
    def clean_text(self, text):
        """Clean and normalize text"""
        if not text:
            return ""
        
        # Remove extra whitespace and newlines
        text = re.sub(r'\s+', ' ', text.strip())
        
        # Remove very short posts (likely spam)
        if len(text) < 10:
            return ""
            
        return text
    
    def collect_reddit_data(self, keyword, limit=200):
        """Collect Reddit posts/comments mentioning keywords - 5 years of data"""
        print(f"Collecting Reddit data for keyword: '{keyword}' (Last 5 years)")
        
        if not self.reddit:
            print("Reddit API not available")
            return []
        
        posts = []
        
        try:
            # Search across all subreddits for the last 5 years
            # Reddit API doesn't support custom date ranges, so we'll get as much as possible
            search_results = self.reddit.subreddit("all").search(
                keyword, 
                sort="new", 
                time_filter="all",  # Get all historical posts
                limit=limit  # Increased limit for 5 years
            )
            
            five_years_ago = datetime.now() - timedelta(days=5*365)
            
            for submission in search_results:
                # Check if post is within last 5 years
                post_date = datetime.fromtimestamp(submission.created_utc)
                if post_date < five_years_ago:
                    continue
                
                # Skip deleted/removed posts
                if submission.selftext == '[deleted]' or submission.selftext == '[removed]':
                    continue
                
                # Combine title and text
                full_text = submission.title
                if submission.selftext:
                    full_text += " " + submission.selftext
                
                clean_text = self.clean_text(full_text)
                if not clean_text:
                    continue
                
                post_data = {
                    'platform': 'reddit',
                    'post_id': submission.id,
                    'text': clean_text,
                    'author': str(submission.author) if submission.author else 'deleted',
                    'timestamp': post_date,
                    'upvotes': submission.score,
                    'comments': submission.num_comments,
                    'likes': 0,  # Reddit doesn't have likes
                    'retweets': 0,  # Reddit doesn't have retweets
                    'followers': 0,  # Reddit doesn't expose follower count
                    'subreddit': submission.subreddit.display_name,
                    'url': submission.url,
                    'keyword_matched': keyword.lower()
                }
                
                posts.append(post_data)
                
                # Small delay to be respectful
                time.sleep(0.1)
        
        except Exception as e:
            print(f"Reddit collection error: {e}")
        
        print(f"✅ Collected {len(posts)} Reddit posts for '{keyword}' (last 5 years)")
        return posts

    def collect_youtube_comments(self, keyword, limit=100):
        """Collect YouTube comments mentioning keywords - Extended search"""
        print(f"Collecting YouTube comments for keyword: '{keyword}' (Extended search)")
        
        if not self.youtube_available:
            print("YouTube API not available")
            return []
        
        comments = []
        
        try:
            # Search for videos from the last 5 years
            five_years_ago = datetime.now() - timedelta(days=5*365)
            published_after = five_years_ago.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # First, search for videos related to the keyword
            search_url = "https://www.googleapis.com/youtube/v3/search"
            search_params = {
                'part': 'snippet',
                'q': keyword,
                'type': 'video',
                'maxResults': 20,  # Search more videos for historical data
                'key': YOUTUBE_API_KEY,
                'order': 'relevance',
                'publishedAfter': published_after  # Last 5 years
            }
            
            search_response = requests.get(search_url, params=search_params)
            search_data = search_response.json()
            
            if 'error' in search_data:
                print(f"YouTube API Error: {search_data['error']['message']}")
                return []
            
            if 'items' not in search_data:
                print(f"No videos found for '{keyword}' in last 5 years")
                return []
            
            # For each video, get comments
            for video in search_data['items'][:10]:  # Top 10 videos
                video_id = video['id']['videoId']
                video_title = video['snippet']['title']
                video_date = datetime.fromisoformat(video['snippet']['publishedAt'].replace('Z', '+00:00'))
                
                # Get comments for this video
                comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
                comments_params = {
                    'part': 'snippet',
                    'videoId': video_id,
                    'maxResults': min(limit // 10, 50),  # Distribute comments across videos
                    'key': YOUTUBE_API_KEY,
                    'order': 'relevance'
                }
                
                comments_response = requests.get(comments_url, params=comments_params)
                comments_data = comments_response.json()
                
                if 'error' in comments_data:
                    print(f"Comments disabled for video: {video_title}")
                    continue
                
                if 'items' in comments_data:
                    for comment_thread in comments_data['items']:
                        comment = comment_thread['snippet']['topLevelComment']['snippet']
                        comment_date = datetime.fromisoformat(comment['publishedAt'].replace('Z', '+00:00'))
                        
                        # Check if comment is within last 5 years (fix timezone comparison)
                        if comment_date.replace(tzinfo=None) < five_years_ago:
                            continue
                        
                        clean_text = self.clean_text(comment['textDisplay'])
                        if not clean_text:
                            continue
                        
                        comment_data = {
                            'platform': 'youtube',
                            'post_id': comment_thread['id'],
                            'text': clean_text,
                            'author': comment['authorDisplayName'],
                            'timestamp': comment_date.replace(tzinfo=None),
                            'likes': comment['likeCount'],
                            'retweets': 0,  # YouTube doesn't have retweets
                            'comments': 0,  # This is already a comment
                            'upvotes': comment['likeCount'],  # Use likes as upvotes
                            'followers': 0,  # Not available via API
                            'verified': False,  # Not easily available
                            'location': "",
                            'video_title': video_title,
                            'video_id': video_id,
                            'video_date': video_date.replace(tzinfo=None),
                            'keyword_matched': keyword.lower()
                        }
                        
                        comments.append(comment_data)
                
                time.sleep(1)  # Longer delay for historical data collection
        
        except Exception as e:
            print(f"YouTube collection error: {e}")
        
        print(f"✅ Collected {len(comments)} YouTube comments for '{keyword}' (last 5 years)")
        return comments

    def collect_facebook_posts(self, keyword, limit=50):
        """Collect Facebook posts mentioning keywords - Historical data"""
        print(f"Collecting Facebook posts for keyword: '{keyword}' (Historical data)")
        print("⚠️ Facebook requires special permissions for public content search")
        
        if not self.facebook_available:
            print("Facebook API not available")
            return []
        
        posts = []
        
        try:
            # Check if we have a real token
            if FACEBOOK_ACCESS_TOKEN == "your_facebook_access_token_here":
                print("Facebook API not configured with real token - skipping")
                return []
            
            print("Note: Facebook public content access is very limited without app review")
            print("Attempting basic page search...")
            
            # Try to search for pages (this will likely fail without proper permissions)
            search_url = f"https://graph.facebook.com/v18.0/search"
            params = {
                'q': keyword,
                'type': 'page',
                'access_token': FACEBOOK_ACCESS_TOKEN,
                'limit': 5
            }
            
            response = requests.get(search_url, params=params)
            data = response.json()
            
            # Check for errors
            if 'error' in data:
                print(f"Facebook API Error: {data['error'].get('message', 'Unknown error')}")
                print("This is expected - Facebook requires app review for public content access")
                return []
            
            # If we get here, continue with existing logic but with better error handling
            five_years_ago = datetime.now() - timedelta(days=5*365)
            
            if 'data' in data and len(data['data']) > 0:
                print(f"Found {len(data['data'])} pages to check")
                
                for page in data['data'][:3]:  # Top 3 pages
                    page_id = page['id']
                    
                    # Get posts from this page with date filtering
                    posts_url = f"https://graph.facebook.com/v18.0/{page_id}/posts"
                    posts_params = {
                        'access_token': FACEBOOK_ACCESS_TOKEN,
                        'fields': 'id,message,created_time,likes.summary(true),comments.summary(true)',
                        'limit': limit // 3,  # Distribute across pages
                        'since': five_years_ago.strftime('%Y-%m-%d')  # Last 5 years
                    }
                    
                    posts_response = requests.get(posts_url, params=posts_params)
                    posts_data = posts_response.json()
                    
                    if 'error' in posts_data:
                        print(f"Error accessing page {page['name']}: {posts_data['error']['message']}")
                        continue
                    
                    if 'data' in posts_data:
                        for post in posts_data['data']:
                            if 'message' in post:
                                clean_text = self.clean_text(post['message'])
                                if not clean_text or keyword.lower() not in clean_text.lower():
                                    continue
                                
                                post_date = datetime.fromisoformat(post['created_time'].replace('Z', '+00:00'))
                                
                                # Check if post is within last 5 years
                                if post_date.replace(tzinfo=None) < five_years_ago:
                                    continue
                                
                                post_data = {
                                    'platform': 'facebook',
                                    'post_id': post['id'],
                                    'text': clean_text,
                                    'author': page['name'],
                                    'timestamp': post_date.replace(tzinfo=None),
                                    'likes': post.get('likes', {}).get('summary', {}).get('total_count', 0),
                                    'comments': post.get('comments', {}).get('summary', {}).get('total_count', 0),
                                    'retweets': 0,  # Facebook doesn't have retweets
                                    'upvotes': 0,
                                    'followers': 0,
                                    'verified': False,
                                    'location': "",
                                    'page_name': page['name'],
                                    'keyword_matched': keyword.lower()
                                }
                                
                                posts.append(post_data)
                    
                    time.sleep(2)  # Delay between page requests
            else:
                print("No accessible pages found")
                return []
            
        except Exception as e:
            print(f"Facebook collection error: {e}")
            print("Note: Facebook API requires special permissions for public content access")
        
        print(f"✅ Collected {len(posts)} Facebook posts for '{keyword}' (last 5 years)")
        return posts

    def collect_instagram_posts(self, keyword, limit=50):
        """Collect Instagram posts mentioning keywords - Historical data"""
        print(f"Collecting Instagram posts for keyword: '{keyword}' (Historical data)")
        print("⚠️ Instagram requires Business/Creator account and hashtag-based search")
        
        if not self.instagram_available:
            print("Instagram API not available")
            return []
        
        posts = []
        
        try:
            # Check if we have real credentials
            if INSTAGRAM_ACCESS_TOKEN == "your_instagram_access_token_here":
                print("Instagram API not configured with real token - skipping")
                return []
            
            print("Note: Instagram requires Business account and proper setup")
            print("Skipping Instagram collection for now...")
            
            # For now, return empty list until proper Instagram Business API is set up
            return []
            
            # TODO: Implement proper Instagram Business API integration
            # This requires:
            # 1. Instagram Business Account
            # 2. Facebook Business Manager setup
            # 3. Proper app permissions
            # 4. Real Instagram User ID
            
        except Exception as e:
            print(f"Instagram collection error: {e}")
            print("Note: Instagram API requires Business account and proper app setup")
        
        print(f"✅ Collected {len(posts)} Instagram posts for '{keyword}' (last 5 years)")
        return posts
    
    def collect_all_brand_data(self, keywords=None, reddit_per_keyword=200, 
                              youtube_per_keyword=100, facebook_per_keyword=50, instagram_per_keyword=50):
        """Collect 5 years of data for all brand keywords across all platforms"""
        if keywords is None:
            keywords = BRAND_KEYWORDS  # Use all keywords for historical collection
        
        print(f"🚨 5-YEAR HISTORICAL DATA COLLECTION 🚨")
        print(f"Collecting 5 years of data for {len(keywords)} keywords across all available platforms...")
        print(f"Target per keyword:")
        print(f"  - Reddit: {reddit_per_keyword} posts")
        print(f"  - YouTube: {youtube_per_keyword} comments")
        print(f"  - Facebook: {facebook_per_keyword} posts")
        print(f"  - Instagram: {instagram_per_keyword} posts")
        print("⚠️ This may take 30-60 minutes depending on data availability")
        
        all_posts = []
        
        for i, keyword in enumerate(keywords, 1):
            print(f"\n--- Processing keyword {i}/{len(keywords)}: '{keyword}' ---")
            
            # Collect Reddit data - historical
            if self.reddit:
                try:
                    reddit_posts = self.collect_reddit_data(keyword, reddit_per_keyword)
                    all_posts.extend(reddit_posts)
                    time.sleep(3)  # Longer delay for historical collection
                except Exception as e:
                    print(f"Failed to collect Reddit data for '{keyword}': {e}")
            else:
                print("Skipping Reddit (API not available)")
            
            # Collect YouTube comments - historical
            if self.youtube_available:
                try:
                    youtube_comments = self.collect_youtube_comments(keyword, youtube_per_keyword)
                    all_posts.extend(youtube_comments)
                    time.sleep(3)
                except Exception as e:
                    print(f"Failed to collect YouTube data for '{keyword}': {e}")
            else:
                print("Skipping YouTube (API not available)")
            
            # Collect Facebook posts - historical
            if self.facebook_available:
                try:
                    print("Attempting Facebook collection (may be limited)...")
                    facebook_posts = self.collect_facebook_posts(keyword, facebook_per_keyword)
                    if facebook_posts:
                        all_posts.extend(facebook_posts)
                        print(f"Successfully collected {len(facebook_posts)} Facebook posts")
                    else:
                        print("No Facebook posts collected (expected due to API limitations)")
                    time.sleep(3)
                except Exception as e:
                    print(f"Facebook collection failed for '{keyword}': {e}")
                    print("This is expected - Facebook requires special permissions for public content")
            else:
                print("Skipping Facebook (API not configured)")
            
            # Collect Instagram posts - historical  
            if self.instagram_available:
                try:
                    print("Attempting Instagram collection (requires Business account)...")
                    instagram_posts = self.collect_instagram_posts(keyword, instagram_per_keyword)
                    if instagram_posts:
                        all_posts.extend(instagram_posts)
                        print(f"Successfully collected {len(instagram_posts)} Instagram posts")
                    else:
                        print("No Instagram posts collected (requires proper Business API setup)")
                    time.sleep(3)
                except Exception as e:
                    print(f"Instagram collection failed for '{keyword}': {e}")
                    print("This is expected - Instagram requires Business account setup")
            else:
                print("Skipping Instagram (API not configured)")
            
            # Progress update
            if i < len(keywords):
                print(f"Completed {i}/{len(keywords)} keywords. Pausing 15 seconds before next keyword...")
                time.sleep(15)
        
        print(f"\n🎉 5-year historical data collection complete!")
        print(f"Total posts collected: {len(all_posts)}")
        
        # Summary by platform and year
        platform_counts = {}
        yearly_counts = {}
        
        for post in all_posts:
            platform = post['platform']
            platform_counts[platform] = platform_counts.get(platform, 0) + 1
            
            year = post['timestamp'].year
            yearly_counts[year] = yearly_counts.get(year, 0) + 1
        
        print("\nPlatform breakdown:")
        for platform, count in platform_counts.items():
            print(f"  - {platform.title()}: {count} posts")
        
        print("\nYearly breakdown:")
        for year in sorted(yearly_counts.keys()):
            print(f"  - {year}: {yearly_counts[year]} posts")
        
        return all_posts
    
    def get_api_status(self):
        """Check which APIs are working"""
        status = {
            'reddit': self.reddit is not None,
            'youtube': self.youtube_available,
            'facebook': self.facebook_available,
            'instagram': self.instagram_available
        }
        
        print("\n--- API Status ---")
        print(f"Reddit API: {'✅ Connected' if status['reddit'] else '❌ Not available'}")
        print(f"YouTube API: {'✅ Connected' if status['youtube'] else '❌ Not available'}")
        print(f"Facebook API: {'✅ Connected' if status['facebook'] else '❌ Not available'}")
        print(f"Instagram API: {'✅ Connected' if status['instagram'] else '❌ Not available'}")
        
        return status


def test_collector():
    """Test the data collector with a small sample"""
    print("Testing Social Media Collector...")
    print("=" * 50)
    
    collector = SocialMediaCollector()
    
    # Check API status first
    status = collector.get_api_status()
    
    if not any(status.values()):
        print("\n❌ No APIs available. Please check your credentials.")
        return []
    
    # Test with one keyword and small limits
    print(f"\nTesting with keyword 'bacardi' (Test Mode - Small Sample)...")
    test_posts = collector.collect_all_brand_data(
        keywords=['bacardi'],  # Only 1 keyword for testing
        reddit_per_keyword=10,  # Small samples for testing
        youtube_per_keyword=8,
        facebook_per_keyword=5,
        instagram_per_keyword=5
    )
    
    if test_posts:
        print("\n--- Sample Posts ---")
        for i, post in enumerate(test_posts[:3]):
            print(f"\nPost {i+1}:")
            print(f"Platform: {post['platform']}")
            print(f"Author: {post['author']}")
            print(f"Text: {post['text'][:100]}...")
            print(f"Timestamp: {post['timestamp']}")
            if post['platform'] == 'reddit':
                print(f"Upvotes: {post['upvotes']}, Comments: {post['comments']}")
            elif post['platform'] == 'youtube':
                print(f"Video: {post.get('video_title', 'N/A')}, Likes: {post['likes']}")
            elif post['platform'] == 'facebook':
                print(f"Page: {post.get('page_name', 'N/A')}, Likes: {post['likes']}")
            elif post['platform'] == 'instagram':
                print(f"Hashtag: {post.get('hashtag', 'N/A')}, Likes: {post['likes']}")
    
    return test_posts


def collect_and_save():
    """Collect 5 years of data and save to database"""
    try:
        from database import DatabaseManager
    except ImportError:
        print("❌ Database module not found. Make sure database.py exists.")
        return []
    
    print("Starting 5-year historical data collection and save process...")
    print("=" * 50)
    
    # Initialize
    collector = SocialMediaCollector()
    db = DatabaseManager()
    
    # Check API status
    status = collector.get_api_status()
    if not any(status.values()):
        print("\n❌ No APIs available. Cannot collect data.")
        return []
    
    # Collect 5 years of data - FULL COLLECTION
    posts = collector.collect_all_brand_data(
        keywords=BRAND_KEYWORDS,  # All brand keywords
        reddit_per_keyword=200,   # 200 Reddit posts per keyword
        youtube_per_keyword=100,  # 100 YouTube comments per keyword
        facebook_per_keyword=50,  # 50 Facebook posts per keyword
        instagram_per_keyword=50  # 50 Instagram posts per keyword
    )
    
    if posts:
        # Save to database
        saved_count = db.save_posts(posts)
        
        print(f"\n✅ Saved {saved_count} posts to database!")
        
        # Show database stats
        stats = db.get_database_stats()
        print(f"Total posts in database: {stats['total_posts']}")
        print(f"Platform breakdown: {stats['platform_breakdown']}")
        
        return posts
    else:
        print("\n❌ No posts collected")
        return []


if __name__ == "__main__":
    print("Bacardi Social Media Data Collector - 5 Year Historical Analysis")
    print("=" * 60)
    
    # Show current config status
    print(f"Reddit Credentials: {'✅ Loaded' if REDDIT_CLIENT_ID and REDDIT_CLIENT_ID != 'your_reddit_client_id' else '❌ Not configured'}")
    print(f"YouTube API Key: {'✅ Loaded' if YOUTUBE_API_KEY and YOUTUBE_API_KEY != 'your_youtube_api_key_here' else '❌ Not configured'}")
    print(f"Facebook Token: {'✅ Loaded' if FACEBOOK_ACCESS_TOKEN and FACEBOOK_ACCESS_TOKEN != 'your_facebook_access_token_here' else '❌ Not configured'}")
    print(f"Instagram Token: {'✅ Loaded' if INSTAGRAM_ACCESS_TOKEN and INSTAGRAM_ACCESS_TOKEN != 'your_instagram_access_token_here' else '❌ Not configured'}")
    
    choice = input("""
    Choose an option:
    1. Test collector (small sample - quick test)
    2. Collect 5 years of data and save to database (FULL COLLECTION - 30-60 mins)
    3. Check API status only
    4. Collect from specific platform only (5 years)
    5. Exit
    
    Enter choice (1-5): """)
    
    if choice == "1":
        posts = test_collector()
        if posts:
            print(f"\n✅ Test successful! Collected {len(posts)} posts")
        else:
            print("\n❌ Test failed. Check API credentials.")
    
    elif choice == "2":
        print("⚠️ WARNING: This will collect 5 years of historical data.")
        print("This process may take 30-60 minutes and use significant API quota.")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        
        if confirm.lower() == 'yes':
            posts = collect_and_save()
            if posts:
                print("\n🎉 Ready to run dashboard: streamlit run dashboard.py")
            else:
                print("\n❌ Collection failed. Check API credentials.")
        else:
            print("Collection cancelled.")
    
    elif choice == "3":
        collector = SocialMediaCollector()
        collector.get_api_status()
    
    elif choice == "4":
        platform_choice = input("""
        Choose platform (5-year collection):
        1. Reddit only  
        2. YouTube only
        3. Facebook only
        4. Instagram only
        
        Enter choice (1-4): """)
        
        collector = SocialMediaCollector()
        
        # Import database components with error handling
        try:
            from database import DatabaseManager
            db = DatabaseManager()
        except ImportError:
            print("❌ Database module not found. Make sure database.py exists.")
            db = None
        
        posts = []
        
        print("⚠️ Collecting 5 years of data for single platform...")
        
        if platform_choice == "1" and collector.reddit:
            posts = collector.collect_reddit_data('bacardi', 300)  # More for single platform
        elif platform_choice == "2" and collector.youtube_available:
            posts = collector.collect_youtube_comments('bacardi', 150)
        elif platform_choice == "3" and collector.facebook_available:
            posts = collector.collect_facebook_posts('bacardi', 100)
        elif platform_choice == "4" and collector.instagram_available:
            posts = collector.collect_instagram_posts('bacardi', 100)
        else:
            print("Platform not available or invalid choice")
            
        if posts and db:
            # Add sentiment analysis
            try:
                from sentiment_analyzer import SentimentAnalyzer
                analyzer = SentimentAnalyzer()
                
                print("Analyzing sentiment...")
                for post in posts:
                    sentiment = analyzer.analyze_sentiment(post['text'])
                    post.update(sentiment)
                
                saved_count = db.save_posts(posts)
                print(f"\n✅ Saved {saved_count} posts from single platform (5 years)!")
            except ImportError:
                print("❌ SentimentAnalyzer not found. Posts collected but not analyzed.")
                print(f"Collected {len(posts)} posts - you can analyze them later")
                
                # Save without sentiment analysis
                saved_count = db.save_posts(posts)
                print(f"✅ Saved {saved_count} posts without sentiment analysis")
        elif posts:
            print(f"✅ Collected {len(posts)} posts but couldn't save to database")
            print("Posts collected successfully - database module not available")
        else:
            print("❌ No posts collected or platform not available")
    
    elif choice == "5":
        print("Goodbye!")
    
    else:
        print("Invalid choice")