import subprocess
import sys
import os
from database import DatabaseManager
import config

class SimpleDataCollector:
    def __init__(self):
        self.db = DatabaseManager()
    
    def run_api_collection(self, keywords):
        """Run API collection using the original data_collector.py"""
        print("\n📡 Running API Data Collection")
        print("=" * 40)
        
        try:
            from data_collector import EnhancedDataCollector
            
            collector = EnhancedDataCollector()
            all_posts = []
            
            for keyword in keywords:
                print(f"\n🔍 Collecting data for: {keyword}")
                
                # Reddit collection
                reddit_posts = collector.collect_reddit_posts(keyword, limit=100)
                if reddit_posts:
                    all_posts.extend(reddit_posts)
                    print(f"   📊 Reddit: {len(reddit_posts)} posts")
                
                # Save Reddit posts
                saved_count = 0
                for post in reddit_posts:
                    try:
                        if collector.save_post(post):
                            saved_count += 1
                    except Exception as e:
                        print(f"Error saving Reddit post: {e}")
                        continue
                
                # YouTube collection
                youtube_posts = collector.collect_youtube_comments(keyword, limit=100)
                if youtube_posts:
                    all_posts.extend(youtube_posts)
                    print(f"   📺 YouTube: {len(youtube_posts)} comments")
                
                # Save YouTube posts
                for post in youtube_posts:
                    try:
                        if collector.save_post(post):
                            saved_count += 1
                    except Exception as e:
                        print(f"Error saving YouTube post: {e}")
                        continue
                
                print(f"   💾 Saved: {saved_count} posts for '{keyword}'")
            
            print(f"\n✅ API Collection Complete!")
            print(f"📊 Total posts collected: {len(all_posts)}")
            
            return all_posts
            
        except Exception as e:
            print(f"❌ API collection failed: {e}")
            return []
    
    def run_web_scraping(self, keywords):
        """Run web scraping in a separate process to avoid async conflicts"""
        print("\n🌐 Running Web Scraping")
        print("=" * 40)
        
        try:
            # Create a simple script to run web scraping
            scraping_script = '''
import asyncio
import sys
sys.path.append('.')

async def run_scraping():
    try:
        from web_scraper import AdvancedWebScraper
        scraper = AdvancedWebScraper()
        keywords = {keywords}
        posts = await scraper.comprehensive_scrape(keywords, limit_per_source=30)
        print(f"Scraping completed: {{len(posts)}} posts collected")
        return len(posts)
    except Exception as e:
        print(f"Scraping error: {{e}}")
        return 0

if __name__ == "__main__":
    result = asyncio.run(run_scraping())
    sys.exit(0 if result > 0 else 1)
'''.format(keywords=keywords)
            
            # Write temporary script
            with open('temp_scraper.py', 'w') as f:
                f.write(scraping_script)
            
            # Run the scraping script
            result = subprocess.run([sys.executable, 'temp_scraper.py'], 
                                  capture_output=True, text=True, timeout=1800)  # 30 min timeout
            
            # Clean up
            if os.path.exists('temp_scraper.py'):
                os.remove('temp_scraper.py')
            
            if result.returncode == 0:
                print("✅ Web scraping completed successfully!")
                print(result.stdout)
                return True
            else:
                print("❌ Web scraping failed:")
                print(result.stderr)
                return False
                
        except subprocess.TimeoutExpired:
            print("⏰ Web scraping timed out (30 minutes)")
            return False
        except Exception as e:
            print(f"❌ Web scraping error: {e}")
            return False
    
    def collect_data(self, keywords=None, use_api=True, use_scraping=False):
        """Main data collection method"""
        if keywords is None:
            keywords = getattr(config, 'BRAND_KEYWORDS', ['bacardi', 'breezer'])
        
        print("🚀 Simple Data Collection")
        print("=" * 50)
        print(f"📊 Keywords: {', '.join(keywords)}")
        print(f"📡 API Collection: {'Yes' if use_api else 'No'}")
        print(f"🌐 Web Scraping: {'Yes' if use_scraping else 'No'}")
        
        results = []
        
        # Run API collection
        if use_api:
            api_posts = self.run_api_collection(keywords)
            results.extend(api_posts)
        
        # Run web scraping
        if use_scraping:
            scraping_success = self.run_web_scraping(keywords)
            if scraping_success:
                print("Web scraping data has been saved to database")
        
        # Generate final summary
        self.generate_summary()
        
        return results
    
    def generate_summary(self):
        """Generate collection summary"""
        print(f"\n📋 COLLECTION SUMMARY")
        print("=" * 30)
        
        try:
            import sqlite3
            conn = sqlite3.connect(self.db.db_path)
            
            # Get basic stats
            cursor = conn.execute('''
                SELECT 
                    COUNT(*) as total,
                    COUNT(DISTINCT platform) as platforms,
                    MAX(timestamp) as latest
                FROM social_posts
            ''')
            
            stats = cursor.fetchone()
            print(f"📊 Total Posts: {stats[0]:,}")
            print(f"🌐 Platforms: {stats[1]}")
            if stats[2]:
                print(f"📅 Latest Post: {stats[2][:19]}")
            
            # Platform breakdown
            cursor = conn.execute('''
                SELECT platform, COUNT(*) as count
                FROM social_posts
                GROUP BY platform
                ORDER BY count DESC
            ''')
            
            print(f"\n📱 Platform Breakdown:")
            for row in cursor.fetchall():
                print(f"   {row[0].title()}: {row[1]:,} posts")
            
            # Recent posts
            cursor = conn.execute('''
                SELECT COUNT(*) as recent_count
                FROM social_posts
                WHERE timestamp >= datetime('now', '-1 day')
            ''')
            
            recent = cursor.fetchone()[0]
            print(f"\n🕐 Posts in last 24h: {recent:,}")
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Error generating summary: {e}")
        
        print(f"\n🎯 Next Steps:")
        print(f"1. Run sentiment analysis: python analyze_sentiment.py")
        print(f"2. Launch dashboard: streamlit run dashboard.py")

def main():
    """Main function"""
    print("🚀 Simple Bacardi Data Collector")
    print("🔄 Conflict-Free Data Collection")
    print("=" * 50)
    
    collector = SimpleDataCollector()
    
    # Collection options
    print("\n📋 Collection Options:")
    print("1. API Only (Reddit + YouTube) - Safe & Fast")
    print("2. API + Web Scraping - Comprehensive")
    print("3. Custom Keywords (API Only)")
    print("4. Quick Test")
    
    choice = input("\nSelect option (1-4): ").strip()
    
    # Default keywords
    keywords = ['bacardi', 'breezer', 'captain morgan', 'malibu']
    
    if choice == "1":
        # API only - safest option
        print(f"\n📡 API Only Collection")
        print(f"📊 Keywords: {', '.join(keywords)}")
        print(f"⏱️ Estimated time: 5-10 minutes")
        print(f"✅ No async conflicts")
        
        confirm = input("Proceed? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.collect_data(keywords, use_api=True, use_scraping=False)
    
    elif choice == "2":
        # API + Web scraping
        print(f"\n🔄 API + Web Scraping")
        print(f"📊 Keywords: {', '.join(keywords)}")
        print(f"⏱️ Estimated time: 15-30 minutes")
        print(f"⚠️ May have some conflicts - uses subprocess isolation")
        
        confirm = input("Proceed? (y/n): ").lower().strip()
        if confirm == 'y':
            collector.collect_data(keywords, use_api=True, use_scraping=True)
    
    elif choice == "3":
        # Custom keywords
        print(f"\n🎯 Custom Keywords (API Only)")
        custom_input = input("Enter keywords (comma-separated): ").strip()
        if custom_input:
            custom_keywords = [k.strip() for k in custom_input.split(',')]
            print(f"📊 Using keywords: {', '.join(custom_keywords)}")
            collector.collect_data(custom_keywords, use_api=True, use_scraping=False)
        else:
            print("❌ No keywords provided")
    
    elif choice == "4":
        # Quick test
        print(f"\n⚡ Quick Test")
        test_keywords = ['bacardi']
        print(f"📊 Testing with: {', '.join(test_keywords)}")
        collector.collect_data(test_keywords, use_api=True, use_scraping=False)
    
    else:
        print("❌ Invalid choice. Exiting.")
        return

if __name__ == "__main__":
    main()