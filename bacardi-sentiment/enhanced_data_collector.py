import asyncio
import subprocess
import sys
import os
from database import DatabaseManager
import config

class HybridDataCollector:
    def __init__(self):
        self.db = DatabaseManager()
    
    def run_sync_api_collection(self, keywords):
        """Run synchronous API collection in separate process"""
        print("\n📡 Phase 1: API Data Collection (Synchronous)")
        print("-" * 40)
        
        try:
            # Import and run sync collector
            from data_collector import EnhancedDataCollector
            
            api_collector = EnhancedDataCollector()
            all_posts = []
            
            for keyword in keywords:
                print(f"\n🔍 API Collection for: {keyword}")
                
                # Reddit API
                reddit_posts = api_collector.collect_reddit_posts(keyword, limit=100)
                if reddit_posts:
                    all_posts.extend(reddit_posts)
                    print(f"   📊 Reddit: {len(reddit_posts)} posts")
                
                # YouTube API
                youtube_posts = api_collector.collect_youtube_comments(keyword, limit=100)
                if youtube_posts:
                    all_posts.extend(youtube_posts)
                    print(f"   📺 YouTube: {len(youtube_posts)} comments")
                
                # Save posts immediately
                saved_count = 0
                for post in reddit_posts + youtube_posts:
                    try:
                        if api_collector.save_post(post):
                            saved_count += 1
                    except Exception as e:
                        print(f"Error saving post: {e}")
                        continue
                
                print(f"   💾 Saved: {saved_count} posts")
            
            print(f"\n✅ API Collection complete: {len(all_posts)} posts")
            return all_posts
            
        except Exception as e:
            print(f"⚠️ API collection error: {e}")
            return []
    
    async def run_async_web_scraping(self, keywords):
        """Run asynchronous web scraping"""
        print(f"\n🌐 Phase 2: Web Scraping (Asynchronous)")
        print("-" * 40)
        
        try:
            from web_scraper import AdvancedWebScraper
            
            scraper = AdvancedWebScraper()
            scraped_posts = await scraper.comprehensive_scrape(
                keywords=keywords, 
                limit_per_source=50
            )
            
            print(f"\n✅ Web scraping complete: {len(scraped_posts)} posts")
            return scraped_posts
            
        except Exception as e:
            print(f"⚠️ Web scraping error: {e}")
            return []
    
    def collect_all_data(self, keywords=None, use_api=True, use_scraping=True):
        """Collect data using both API and scraping methods"""
        if keywords is None:
            keywords = getattr(config, 'BRAND_KEYWORDS', ['bacardi', 'breezer'])
        
        all_posts = []
        
        print("🚀 Starting Hybrid Data Collection")
        print("=" * 50)
        
        # Phase 1: Synchronous API Collection
        if use_api:
            api_posts = self.run_sync_api_collection(keywords)
            all_posts.extend(api_posts)
        
        # Phase 2: Asynchronous Web Scraping
        if use_scraping:
            try:
                # Run async scraping
                scraped_posts = asyncio.run(self.run_async_web_scraping(keywords))
                all_posts.extend(scraped_posts)
            except Exception as e:
                print(f"⚠️ Async scraping error: {e}")
                print("Skipping web scraping phase...")
        
        print(f"\n🎉 Total Collection Complete!")
        print(f"📊 Total posts collected: {len(all_posts)}")
        
        # Generate summary
        self.generate_collection_summary()
        
        return all_posts
    
    def generate_collection_summary(self):
        """Generate a comprehensive summary of collected data"""
        print(f"\n📋 DATA COLLECTION SUMMARY")
        print("=" * 40)
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            
            # Overall stats
            stats_query = '''
            SELECT 
                COUNT(*) as total_posts,
                COUNT(DISTINCT platform) as platforms,
                COUNT(DISTINCT brand_category) as brand_categories,
                MIN(timestamp) as earliest,
                MAX(timestamp) as latest
            FROM social_posts
            '''
            
            cursor = conn.execute(stats_query)
            stats = cursor.fetchone()
            
            print(f"📊 Total Posts: {stats[0]:,}")
            print(f"🌐 Platforms: {stats[1]}")
            print(f"🏢 Brand Categories: {stats[2]}")
            if stats[3] and stats[4]:
                print(f"📅 Date Range: {stats[3][:10]} to {stats[4][:10]}")
            
            # Platform breakdown
            platform_query = '''
            SELECT platform, COUNT(*) as count
            FROM social_posts
            GROUP BY platform
            ORDER BY count DESC
            '''
            
            print(f"\n📱 Platform Breakdown:")
            cursor = conn.execute(platform_query)
            for row in cursor.fetchall():
                print(f"   {row[0].title()}: {row[1]:,} posts")
            
            # Brand category breakdown
            brand_query = '''
            SELECT brand_category, COUNT(*) as count
            FROM social_posts
            WHERE brand_category IS NOT NULL
            GROUP BY brand_category
            ORDER BY count DESC
            '''
            
            print(f"\n🏢 Brand Category Breakdown:")
            cursor = conn.execute(brand_query)
            for row in cursor.fetchall():
                print(f"   {row[0].title().replace('_', ' ')}: {row[1]:,} posts")
            
            # Recent activity
            recent_query = '''
            SELECT platform, COUNT(*) as count
            FROM social_posts
            WHERE timestamp >= datetime('now', '-24 hours')
            GROUP BY platform
            ORDER BY count DESC
            '''
            
            print(f"\n🕐 Last 24 Hours Activity:")
            cursor = conn.execute(recent_query)
            recent_data = cursor.fetchall()
            if recent_data:
                for row in recent_data:
                    print(f"   {row[0].title()}: {row[1]:,} posts")
            else:
                print("   No recent activity")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error generating summary: {e}")
        
        print(f"\n🎯 Next Steps:")
        print(f"1. Run sentiment analysis: python analyze_sentiment.py")
        print(f"2. Launch dashboard: streamlit run dashboard.py")
        print(f"3. Check database: {self.db.db_path}")

def main():
    """Main execution function"""
    print("🚀 Enhanced Bacardi Data Collector")
    print("🔄 Hybrid Approach (Sequential API + Async Scraping)")
    print("=" * 50)
    
    collector = HybridDataCollector()
    
    # Collection options
    print("\n📋 Collection Options:")
    print("1. Full Hybrid Collection (API + Scraping) - Recommended")
    print("2. API Only (Reddit + YouTube)")
    print("3. Web Scraping Only (Social Media + Reviews + News)")
    print("4. Custom Keywords")
    print("5. Quick Test (Limited data)")
    
    choice = input("\nSelect option (1-5): ").strip()
    
    # Default keywords
    keywords = ['bacardi', 'breezer', 'captain morgan', 'malibu']
    
    if choice == "1":
        # Full hybrid collection
        print(f"\n🎯 Full Hybrid Collection")
        print(f"📊 Keywords: {', '.join(keywords)}")
        print(f"⏱️ Estimated time: 20-40 minutes")
        
        confirm = input("Proceed? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.collect_all_data(keywords, use_api=True, use_scraping=True)
    
    elif choice == "2":
        # API only
        print(f"\n📡 API Only Collection")
        print(f"📊 Keywords: {', '.join(keywords)}")
        print(f"⏱️ Estimated time: 5-10 minutes")
        
        confirm = input("Proceed? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.collect_all_data(keywords, use_api=True, use_scraping=False)
    
    elif choice == "3":
        # Web scraping only
        print(f"\n🌐 Web Scraping Only")
        print(f"📊 Keywords: {', '.join(keywords)}")
        print(f"⏱️ Estimated time: 15-30 minutes")
        
        confirm = input("Proceed? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.collect_all_data(keywords, use_api=False, use_scraping=True)
    
    elif choice == "4":
        # Custom keywords
        print(f"\n🎯 Custom Keywords")
        custom_input = input("Enter keywords (comma-separated): ").strip()
        if custom_input:
            custom_keywords = [k.strip() for k in custom_input.split(',')]
            print(f"📊 Using keywords: {', '.join(custom_keywords)}")
            
            method = input("Use API+Scraping (1), API only (2), or Scraping only (3)? ").strip()
            use_api = method in ['1', '2']
            use_scraping = method in ['1', '3']
            
            collector.collect_all_data(custom_keywords, use_api=use_api, use_scraping=use_scraping)
        else:
            print("❌ No keywords provided")
    
    elif choice == "5":
        # Quick test
        print(f"\n⚡ Quick Test Collection")
        test_keywords = ['bacardi']
        print(f"📊 Testing with: {', '.join(test_keywords)}")
        print(f"⏱️ Estimated time: 5 minutes")
        
        collector.collect_all_data(test_keywords, use_api=True, use_scraping=False)
    
    else:
        print("❌ Invalid choice. Exiting.")
        return

if __name__ == "__main__":
    main()