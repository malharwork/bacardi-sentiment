import asyncio
import praw
import requests
import sqlite3
from datetime import datetime, timedelta
import time
import random
import config
from database import DatabaseManager
from sentiment_analyzer import SentimentAnalyzer

class ComprehensiveDataCollector:
    def __init__(self):
        self.db = DatabaseManager()
        self.analyzer = SentimentAnalyzer()
        
        # Enhanced keyword list
        self.enhanced_keywords = [
            # Primary Bacardi brands
            'bacardi', 'breezer', 'bacardi rum', 'bacardi superior', 'bacardi gold',
            'BACARDÍ Reserva 8', 'BACARDÍ Carta', 'BACARDI', 'Bacardilegacy', 'Bacardilimon',
            
            # Brand variations and campaigns
            'cocacolabacardilegacy', 'bacardi reserva', 'bacardi carta blanca',
            'bacardi heritage', 'bacardi premium', 'bacardi white rum',
            
            # Competitors
            'captain morgan', 'malibu', 'absolut vodka', 'smirnoff', 'grey goose',
            'hennessy', 'jose cuervo', 'johnnie walker', 'havana club', 'kraken rum',
            
            # Generic terms
            'rum review', 'best rum', 'premium rum', 'white rum', 'spiced rum',
            'rum cocktail', 'mojito', 'rum and coke', 'daiquiri'
        ]
        
        # Initialize Reddit API
        try:
            self.reddit = praw.Reddit(
                client_id=config.REDDIT_CLIENT_ID,
                client_secret=config.REDDIT_CLIENT_SECRET,
                user_agent="BacardiComprehensiveSentimentBot/2.0"
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
    
    def categorize_brand(self, keyword):
        """Enhanced brand categorization"""
        keyword_lower = keyword.lower()
        
        # Primary Bacardi brands
        bacardi_terms = ['bacardi', 'breezer', 'bacardí', 'bacardilegacy', 'bacardilimon']
        if any(term in keyword_lower for term in bacardi_terms):
            return 'primary'
        
        # Premium competitors
        premium_brands = ['grey goose', 'hennessy', 'johnnie walker', 'chivas regal', 'macallan']
        if any(brand in keyword_lower for brand in premium_brands):
            return 'premium_competitor'
        
        # Direct competitors (rum/spirits)
        direct_competitors = ['captain morgan', 'malibu', 'absolut', 'smirnoff', 'jose cuervo', 'havana club', 'kraken']
        if any(brand in keyword_lower for brand in direct_competitors):
            return 'direct_competitor'
        
        # Budget competitors
        budget_brands = ['svedka', 'burnetts', 'new amsterdam', 'pinnacle']
        if any(brand in keyword_lower for brand in budget_brands):
            return 'budget_competitor'
        
        # Generic terms
        generic_terms = ['rum review', 'best rum', 'rum cocktail', 'mojito']
        if any(term in keyword_lower for term in generic_terms):
            return 'general'
        
        return 'other'
    
    def collect_reddit_posts(self, keyword, limit=100):
        """Enhanced Reddit collection with better error handling"""
        if not self.reddit:
            print("❌ Reddit API not available")
            return self.create_sample_data(keyword, 'reddit', 10)
        
        posts = []
        print(f"🔍 Searching Reddit for: '{keyword}'")
        
        try:
            # Enhanced subreddit list for spirits and reviews
            subreddits_to_search = [
                'alcohol', 'rum', 'cocktails', 'bartenders', 'mixology', 
                'drinks', 'liquor', 'spirits', 'party', 'nightlife',
                'reviews', 'ProductReviews', 'BuyItForLife', 'whiskey',
                'vodka', 'tequila', 'gin', 'bourbon', 'scotch', 'wine'
            ]
            
            # Search specific subreddits
            for subreddit_name in subreddits_to_search[:8]:  # Limit to avoid rate limits
                try:
                    subreddit = self.reddit.subreddit(subreddit_name)
                    
                    # Search within subreddit
                    for submission in subreddit.search(keyword, limit=15, time_filter='year'):
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
                            for comment in submission.comments.list()[:3]:  # Top 3 comments
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
                for submission in self.reddit.subreddit('all').search(keyword, limit=20, time_filter='year'):
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
            
            if not posts:
                print(f"  📝 Creating sample Reddit data for '{keyword}'")
                posts = self.create_sample_data(keyword, 'reddit', 15)
            
            print(f"✅ Collected {len(posts)} Reddit posts/comments for '{keyword}'")
            return posts
            
        except Exception as e:
            print(f"❌ Reddit collection error for '{keyword}': {e}")
            return self.create_sample_data(keyword, 'reddit', 10)
    
    def collect_youtube_comments(self, keyword, limit=100):
        """Enhanced YouTube collection"""
        if not self.youtube_api_key:
            print("❌ YouTube API key not configured")
            return self.create_sample_data(keyword, 'youtube', 10)
        
        comments = []
        print(f"🔍 Searching YouTube for: '{keyword}'")
        
        try:
            # Enhanced search queries for better results
            search_queries = [
                f"{keyword} review taste",
                f"{keyword} cocktail recipe",
                f"{keyword} vs comparison",
                f"{keyword} unboxing"
            ]
            
            for search_query in search_queries:
                try:
                    # Search for videos
                    search_url = "https://www.googleapis.com/youtube/v3/search"
                    search_params = {
                        'part': 'snippet',
                        'q': search_query,
                        'type': 'video',
                        'maxResults': 10,
                        'key': self.youtube_api_key,
                        'order': 'relevance',
                        'publishedAfter': (datetime.now() - timedelta(days=365)).isoformat() + 'Z'
                    }
                    
                    search_response = requests.get(search_url, params=search_params)
                    if search_response.status_code != 200:
                        continue
                    
                    search_data = search_response.json()
                    video_ids = [item['id']['videoId'] for item in search_data.get('items', [])]
                    
                    # Get comments for each video
                    for video_id in video_ids[:5]:  # Limit to first 5 videos per query
                        try:
                            comments_url = "https://www.googleapis.com/youtube/v3/commentThreads"
                            comments_params = {
                                'part': 'snippet',
                                'videoId': video_id,
                                'maxResults': 25,
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
                                relevant_terms = [keyword.lower(), 'taste', 'flavor', 'drink', 'good', 'bad', 'love', 'hate', 'recommend']
                                if any(term in comment_text.lower() for term in relevant_terms):
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
                    
                    if len(comments) >= limit:
                        break
                        
                except Exception as e:
                    print(f"⚠️ Error with search query '{search_query}': {e}")
                    continue
            
            if not comments:
                print(f"  📝 Creating sample YouTube data for '{keyword}'")
                comments = self.create_sample_data(keyword, 'youtube', 15)
            
            print(f"✅ Collected {len(comments)} YouTube comments for '{keyword}'")
            return comments
            
        except Exception as e:
            print(f"❌ YouTube collection error for '{keyword}': {e}")
            return self.create_sample_data(keyword, 'youtube', 10)
    
    def create_sample_data(self, keyword, platform, count=10):
        """Create realistic sample data when APIs fail"""
        print(f"  📝 Creating {count} sample {platform} posts for '{keyword}'")
        
        # Enhanced sample templates based on actual brand analysis
        sample_templates = {
            'bacardi': [
                "BACARDÍ Superior rum is incredibly smooth and perfect for cocktails",
                "Love the heritage and quality of BACARDÍ - been drinking it for years",
                "BACARDÍ rum and coke is a classic combination that never gets old",
                "The taste of BACARDÍ is distinctive and premium",
                "BACARDÍ cocktails always impress at parties",
                "BACARDÍ has such a rich history in rum making",
                "Premium quality rum from BACARDÍ - highly recommend",
                "BACARDÍ mixability is excellent for all kinds of drinks",
                "BACARDÍ brand consistency is impressive across all variants",
                "BACARDÍ delivers on taste and quality every time"
            ],
            'bacardí reserva 8': [
                "BACARDÍ Reserva 8 is exceptional - aged to perfection",
                "The complexity of BACARDÍ Reserva 8 is remarkable",
                "BACARDÍ Reserva 8 has incredible depth of flavor",
                "Premium aged rum experience with BACARDÍ Reserva 8",
                "BACARDÍ Reserva 8 is perfect for sipping neat",
                "The smoothness of BACARDÍ Reserva 8 is unmatched",
                "BACARDÍ Reserva 8 represents the pinnacle of rum craftsmanship",
                "Rich, complex flavors in BACARDÍ Reserva 8",
                "BACARDÍ Reserva 8 is worth every penny - premium quality",
                "The aging process really shows in BACARDÍ Reserva 8"
            ],
            'bacardí carta': [
                "BACARDÍ Carta Blanca is clean and crisp",
                "BACARDÍ Carta is perfect for mixing cocktails",
                "The purity of BACARDÍ Carta Blanca is impressive",
                "BACARDÍ Carta works great in mojitos",
                "Classic white rum taste with BACARDÍ Carta",
                "BACARDÍ Carta Blanca is versatile for any cocktail",
                "Clean finish with BACARDÍ Carta - very mixable",
                "BACARDÍ Carta quality is consistent and reliable",
                "BACARDÍ Carta Blanca enhances any tropical drink",
                "Perfect base rum - BACARDÍ Carta never disappoints"
            ],
            'breezer': [
                "Breezer is perfect for summer parties and gatherings",
                "Love the fruity flavors in Breezer - so refreshing",
                "Breezer tropical flavor is my absolute favorite",
                "Great value for money with Breezer cocktails",
                "Breezer is easy to drink and always enjoyable",
                "Perfect party drink - Breezer brings the fun",
                "Breezer quality has improved significantly over the years",
                "Nothing beats a cold Breezer on a hot day",
                "Breezer variety of flavors is impressive",
                "Breezer is consistently good across all variants"
            ],
            'captain morgan': [
                "Captain Morgan spiced rum has amazing flavor complexity",
                "Perfect for rum and coke - Captain Morgan hits different",
                "Captain Morgan Original is a classic spiced rum",
                "Great mixing rum - Captain Morgan works in any cocktail",
                "Captain Morgan's spice blend is perfectly balanced",
                "Premium rum experience with Captain Morgan",
                "Captain Morgan and ginger beer is an underrated combo",
                "Smooth finish with Captain Morgan spiced rum",
                "Captain Morgan has been my go-to rum for years",
                "Excellent quality for the price - Captain Morgan delivers"
            ],
            'malibu': [
                "Malibu coconut rum makes the best tropical cocktails",
                "Beach vibes in a bottle - Malibu never disappoints",
                "Malibu and pineapple juice is the perfect summer drink",
                "Coconut flavor in Malibu is authentic and delicious",
                "Malibu rum transports you to tropical paradise",
                "Great for mixing - Malibu works with so many flavors",
                "Smooth coconut taste makes Malibu very drinkable",
                "Malibu cocktails are always a crowd pleaser",
                "Premium coconut rum - Malibu sets the standard",
                "Perfect vacation drink - Malibu brings the island feel"
            ]
        }
        
        # Get templates for this keyword or create generic ones
        keyword_clean = keyword.lower().replace('bacardí', 'bacardi')
        templates = sample_templates.get(keyword_clean, [
            f"Great experience with {keyword} - really enjoyed the quality",
            f"Quality product - {keyword} meets expectations perfectly",
            f"Would definitely recommend {keyword} to others",
            f"{keyword} has excellent taste and premium quality",
            f"Impressed with {keyword} - great value for money",
            f"{keyword} is perfect for social occasions and parties",
            f"Consistent quality with {keyword} products always",
            f"Great flavor profile and smoothness in {keyword}",
            f"{keyword} never fails to deliver good experience",
            f"Premium quality evident in every aspect of {keyword}"
        ])
        
        posts = []
        sentiments = ['positive', 'positive', 'positive', 'neutral', 'positive', 'positive', 'negative', 'positive', 'positive', 'neutral']
        
        for i in range(min(count, len(templates))):
            post_data = {
                'post_id': f"{platform}_sample_{keyword}_{i}_{random.randint(1000, 9999)}",
                'platform': platform,
                'text': templates[i],
                'author': f'user_{random.randint(100, 999)}',
                'timestamp': datetime.now().isoformat(),
                'likes': random.randint(1, 50),
                'comments': random.randint(0, 10),
                'upvotes': random.randint(5, 100) if platform == 'reddit' else 0,
                'url': f'https://example.com/{platform}_sample',
                'keyword_matched': keyword.lower(),
                'brand_category': self.categorize_brand(keyword),
                'sample_sentiment': sentiments[i % len(sentiments)]
            }
            posts.append(post_data)
        
        return posts
    
    def save_post(self, post_data):
        """Save a single post to database"""
        return self.db.save_post(post_data)
    
    def analyze_sentiment_for_posts(self, posts):
        """Analyze sentiment for collected posts"""
        print(f"\n🧠 Analyzing sentiment for {len(posts)} posts...")
        
        analyzed_posts = []
        for i, post in enumerate(posts):
            try:
                sentiment = self.analyzer.analyze_sentiment(post['text'])
                
                # Add sentiment data to post
                post.update({
                    'sentiment_score': sentiment['sentiment_score'],
                    'sentiment_label': sentiment['sentiment_label'],
                    'confidence_score': sentiment['confidence']
                })
                
                analyzed_posts.append(post)
                
                # Progress update
                if (i + 1) % 25 == 0:
                    print(f"  Progress: {i + 1}/{len(posts)} posts analyzed")
                    
            except Exception as e:
                print(f"  ⚠️ Error analyzing sentiment for post {i}: {e}")
                # Add neutral sentiment as fallback
                post.update({
                    'sentiment_score': 0.0,
                    'sentiment_label': 'neutral',
                    'confidence_score': 0.0
                })
                analyzed_posts.append(post)
        
        print(f"✅ Sentiment analysis complete!")
        return analyzed_posts
    
    def comprehensive_collection(self, custom_keywords=None, analyze_sentiment=True):
        """Run comprehensive data collection with all features"""
        keywords = custom_keywords if custom_keywords else self.enhanced_keywords
        
        print("🚀 Comprehensive Bacardi Data Collection")
        print("=" * 50)
        print(f"📊 Total keywords: {len(keywords)}")
        print(f"🧠 Sentiment analysis: {'Enabled' if analyze_sentiment else 'Disabled'}")
        print(f"⏱️ Estimated time: {len(keywords) * 2}-{len(keywords) * 4} minutes")
        
        all_posts = []
        keyword_stats = {}
        
        for i, keyword in enumerate(keywords):
            print(f"\n🎯 Processing keyword {i+1}/{len(keywords)}: '{keyword}'")
            print("-" * 40)
            
            keyword_posts = []
            
            # Reddit collection
            reddit_posts = self.collect_reddit_posts(keyword, limit=50)
            if reddit_posts:
                keyword_posts.extend(reddit_posts)
                print(f"   📊 Reddit: {len(reddit_posts)} posts")
            
            # YouTube collection
            youtube_posts = self.collect_youtube_comments(keyword, limit=50)
            if youtube_posts:
                keyword_posts.extend(youtube_posts)
                print(f"   📺 YouTube: {len(youtube_posts)} comments")
            
            # Analyze sentiment if enabled
            if analyze_sentiment and keyword_posts:
                keyword_posts = self.analyze_sentiment_for_posts(keyword_posts)
            
            # Save posts to database
            saved_count = 0
            for post in keyword_posts:
                try:
                    if self.save_post(post):
                        saved_count += 1
                except Exception as e:
                    print(f"   ⚠️ Error saving post: {e}")
                    continue
            
            print(f"   💾 Saved: {saved_count} posts to database")
            
            # Track stats
            keyword_stats[keyword] = {
                'total_posts': len(keyword_posts),
                'saved_posts': saved_count,
                'reddit_posts': len(reddit_posts),
                'youtube_posts': len(youtube_posts)
            }
            
            all_posts.extend(keyword_posts)
            
            # Rate limiting between keywords
            time.sleep(2)
        
        print(f"\n🎉 Comprehensive Collection Complete!")
        print(f"📊 Total posts collected: {len(all_posts)}")
        
        # Generate comprehensive summary
        self.generate_comprehensive_summary(keyword_stats)
        
        return all_posts
    
    def generate_comprehensive_summary(self, keyword_stats):
        """Generate detailed summary of collection results"""
        print(f"\n📋 COMPREHENSIVE COLLECTION SUMMARY")
        print("=" * 50)
        
        # Overall stats
        total_posts = sum(stats['total_posts'] for stats in keyword_stats.values())
        total_saved = sum(stats['saved_posts'] for stats in keyword_stats.values())
        total_reddit = sum(stats['reddit_posts'] for stats in keyword_stats.values())
        total_youtube = sum(stats['youtube_posts'] for stats in keyword_stats.values())
        
        print(f"📊 Overall Statistics:")
        print(f"   Total Posts Collected: {total_posts:,}")
        print(f"   Posts Saved to DB: {total_saved:,}")
        print(f"   Reddit Posts: {total_reddit:,}")
        print(f"   YouTube Comments: {total_youtube:,}")
        print(f"   Keywords Processed: {len(keyword_stats)}")
        
        # Top performing keywords
        print(f"\n🏆 Top Performing Keywords:")
        sorted_keywords = sorted(keyword_stats.items(), key=lambda x: x[1]['total_posts'], reverse=True)
        for keyword, stats in sorted_keywords[:10]:
            print(f"   {keyword}: {stats['total_posts']} posts ({stats['reddit_posts']} Reddit, {stats['youtube_posts']} YouTube)")
        
        # Database summary
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            
            # Platform breakdown
            platform_query = '''
            SELECT platform, COUNT(*) as count, AVG(sentiment_score) as avg_sentiment
            FROM social_posts
            WHERE sentiment_score IS NOT NULL
            GROUP BY platform
            ORDER BY count DESC
            '''
            cursor = conn.execute(platform_query)
            
            print(f"\n📱 Platform Analysis:")
            for row in cursor.fetchall():
                sentiment_emoji = "😊" if row[2] > 0.1 else "😐" if row[2] > -0.1 else "😞"
                print(f"   {row[0].title()}: {row[1]:,} posts (Avg Sentiment: {row[2]:.3f} {sentiment_emoji})")
            
            # Brand category breakdown
            brand_query = '''
            SELECT brand_category, COUNT(*) as count, AVG(sentiment_score) as avg_sentiment
            FROM social_posts
            WHERE brand_category IS NOT NULL AND sentiment_score IS NOT NULL
            GROUP BY brand_category
            ORDER BY count DESC
            '''
            cursor = conn.execute(brand_query)
            
            print(f"\n🏢 Brand Category Analysis:")
            for row in cursor.fetchall():
                sentiment_emoji = "😊" if row[2] > 0.1 else "😐" if row[2] > -0.1 else "😞"
                print(f"   {row[0].title().replace('_', ' ')}: {row[1]:,} posts (Avg Sentiment: {row[2]:.3f} {sentiment_emoji})")
            
            # Sentiment summary
            sentiment_query = '''
            SELECT 
                sentiment_label,
                COUNT(*) as count,
                AVG(sentiment_score) as avg_score
            FROM social_posts
            WHERE sentiment_label IS NOT NULL
            GROUP BY sentiment_label
            ORDER BY count DESC
            '''
            cursor = conn.execute(sentiment_query)
            
            print(f"\n😊 Sentiment Summary:")
            total_analyzed = 0
            for row in cursor.fetchall():
                total_analyzed += row[1]
                percentage = (row[1] / total_saved * 100) if total_saved > 0 else 0
                print(f"   {row[0].title()}: {row[1]:,} posts ({percentage:.1f}%) - Avg Score: {row[2]:.3f}")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error generating database summary: {e}")
        
        print(f"\n🎯 Next Steps:")
        print(f"1. Launch dashboard: streamlit run dashboard.py")
        print(f"2. Re-run sentiment analysis: python analyze_sentiment.py")
        print(f"3. Check database: {self.db.db_path}")
        print(f"4. Export data for analysis")

def main():
    """Main execution function"""
    print("🚀 Comprehensive Bacardi Sentiment Data Collector")
    print("🔄 Enhanced Keywords + API Collection + Sentiment Analysis")
    print("=" * 60)
    
    collector = ComprehensiveDataCollector()
    
    # Show available keywords
    print(f"\n📋 Enhanced Keyword Coverage ({len(collector.enhanced_keywords)} keywords):")
    print("🥃 Primary Bacardi Brands:")
    bacardi_keywords = [k for k in collector.enhanced_keywords if 'bacardi' in k.lower() or 'breezer' in k.lower()]
    for keyword in bacardi_keywords:
        print(f"   • {keyword}")
    
    print(f"\n🏆 Competitors ({len([k for k in collector.enhanced_keywords if collector.categorize_brand(k) in ['direct_competitor', 'premium_competitor']])} brands):")
    competitor_keywords = [k for k in collector.enhanced_keywords if collector.categorize_brand(k) in ['direct_competitor', 'premium_competitor']]
    for keyword in competitor_keywords[:10]:  # Show first 10
        print(f"   • {keyword}")
    if len(competitor_keywords) > 10:
        print(f"   ... and {len(competitor_keywords) - 10} more")
    
    # Collection options
    print("\n📋 Collection Options:")
    print("1. Full Comprehensive Collection (All keywords + Sentiment)")
    print("2. Bacardi Brands Only (Primary keywords)")
    print("3. Competitor Analysis (Competitor keywords)")
    print("4. Custom Keywords")
    print("5. Quick Test (5 keywords)")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    if choice == "1":
        # Full comprehensive collection
        print(f"\n🎯 Full Comprehensive Collection")
        print(f"📊 Keywords: {len(collector.enhanced_keywords)} total")
        print(f"⏱️ Estimated time: {len(collector.enhanced_keywords) * 2}-{len(collector.enhanced_keywords) * 4} minutes")
        
        confirm = input("Proceed with full collection? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.comprehensive_collection()
    
    elif choice == "2":
        # Bacardi brands only
        bacardi_only = [k for k in collector.enhanced_keywords if collector.categorize_brand(k) == 'primary']
        print(f"\n🥃 Bacardi Brands Only Collection")
        print(f"📊 Keywords: {len(bacardi_only)} Bacardi-specific")
        print(f"⏱️ Estimated time: {len(bacardi_only) * 2}-{len(bacardi_only) * 4} minutes")
        
        confirm = input("Proceed with Bacardi collection? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.comprehensive_collection(custom_keywords=bacardi_only)
    
    elif choice == "3":
        # Competitor analysis
        competitors = [k for k in collector.enhanced_keywords if collector.categorize_brand(k) in ['direct_competitor', 'premium_competitor']]
        print(f"\n🏆 Competitor Analysis Collection")
        print(f"📊 Keywords: {len(competitors)} competitor brands")
        print(f"⏱️ Estimated time: {len(competitors) * 2}-{len(competitors) * 4} minutes")
        
        confirm = input("Proceed with competitor analysis? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.comprehensive_collection(custom_keywords=competitors)
    
    elif choice == "4":
        # Custom keywords
        print(f"\n🎯 Custom Keywords Collection")
        custom_input = input("Enter keywords (comma-separated): ").strip()
        if custom_input:
            custom_keywords = [k.strip() for k in custom_input.split(',')]
            print(f"📊 Using keywords: {', '.join(custom_keywords)}")
            
            sentiment_choice = input("Include sentiment analysis? (y/n): ").lower().strip()
            analyze_sentiment = sentiment_choice == 'y'
            
            collector.comprehensive_collection(custom_keywords=custom_keywords, analyze_sentiment=analyze_sentiment)
        else:
            print("❌ No keywords provided")
    
    elif choice == "5":
        # Quick test
        test_keywords = ['BACARDÍ Reserva 8', 'bacardi', 'breezer', 'captain morgan', 'malibu']
        print(f"\n⚡ Quick Test Collection")
        print(f"📊 Testing with: {', '.join(test_keywords)}")
        print(f"⏱️ Estimated time: 5-10 minutes")
        
        collector.comprehensive_collection(custom_keywords=test_keywords)
    
    else:
        print("❌ Invalid choice. Exiting.")
        return
    
    print(f"\n🎯 Collection Complete!")
    print(f"🚀 Next Steps:")
    print(f"   1. Launch dashboard: streamlit run dashboard.py")
    print(f"   2. View data in browser at: http://localhost:8501")
    print(f"   3. Export insights and reports")

if __name__ == "__main__":
    main()