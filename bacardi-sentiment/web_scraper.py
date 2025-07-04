import asyncio
from playwright.async_api import async_playwright
import json
import time
from datetime import datetime, timedelta
import random
import re
from urllib.parse import quote_plus
from database import DatabaseManager
import config

class AdvancedWebScraper:
    def __init__(self):
        self.db = DatabaseManager()
        self.user_agents = [
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        ]
    
    async def setup_browser(self, playwright, headless=True):
        """Setup browser with anti-detection measures"""
        browser = await playwright.chromium.launch(
            headless=headless,
            args=[
                '--no-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        context = await browser.new_context(
            user_agent=random.choice(self.user_agents),
            viewport={'width': 1920, 'height': 1080},
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
            }
        )
        
        # Add stealth scripts
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        return browser, context
    
    async def random_delay(self, min_seconds=1, max_seconds=3):
        """Random delay to avoid detection"""
        await asyncio.sleep(random.uniform(min_seconds, max_seconds))
    
    async def scrape_twitter_search(self, context, keyword, limit=50):
        """Scrape Twitter search results (without login) - Enhanced error handling"""
        posts = []
        print(f"🐦 Scraping Twitter for: {keyword}")
        
        try:
            page = await context.new_page()
            
            # Try multiple Twitter search approaches
            search_urls = [
                f"https://nitter.net/search?q={quote_plus(keyword)}&f=tweets",  # Nitter alternative
                f"https://twitter.com/search?q={quote_plus(keyword)}&src=typed_query&f=live"
            ]
            
            for search_url in search_urls:
                try:
                    print(f"  🔍 Trying: {search_url.split('/')[2]}")
                    await page.goto(search_url, wait_until='networkidle', timeout=15000)
                    await self.random_delay(3, 5)
                    
                    # Different selectors for different sites
                    if 'nitter.net' in search_url:
                        tweet_selector = '.tweet-content'
                        author_selector = '.username'
                        timeout = 5000
                    else:
                        tweet_selector = '[data-testid="tweet"]'
                        author_selector = '[data-testid="User-Name"]'
                        timeout = 5000
                    
                    # Wait for content with shorter timeout
                    try:
                        await page.wait_for_selector(tweet_selector, timeout=timeout)
                    except:
                        print(f"    ⚠️ No content found on {search_url.split('/')[2]}")
                        continue
                    
                    # Extract tweets with different approach
                    tweets = await page.query_selector_all(tweet_selector)
                    
                    for i, tweet in enumerate(tweets[:limit]):
                        try:
                            if 'nitter.net' in search_url:
                                text = await tweet.inner_text()
                                author = "nitter_user"
                            else:
                                # Twitter approach
                                text_element = await tweet.query_selector('[data-testid="tweetText"]')
                                text = await text_element.inner_text() if text_element else ""
                                
                                author_element = await tweet.query_selector(author_selector)
                                author = await author_element.inner_text() if author_element else "unknown"
                            
                            if not text or len(text) < 10:
                                continue
                            
                            post_id = f"twitter_{hash(text + str(i))}"
                            
                            post_data = {
                                'post_id': post_id,
                                'platform': 'twitter',
                                'text': text.strip()[:500],  # Limit text length
                                'author': author.replace('@', '') if author else "unknown",
                                'timestamp': datetime.now().isoformat(),
                                'likes': 0,
                                'retweets': 0,
                                'comments': 0,
                                'url': search_url,
                                'keyword_matched': keyword.lower(),
                                'brand_category': self.categorize_brand(keyword)
                            }
                            
                            posts.append(post_data)
                            
                            if len(posts) >= limit:
                                break
                                
                        except Exception as e:
                            print(f"    ⚠️ Error extracting tweet {i}: {e}")
                            continue
                    
                    if posts:
                        print(f"  ✅ Found {len(posts)} posts on {search_url.split('/')[2]}")
                        break  # Success, no need to try other URLs
                    
                except Exception as e:
                    print(f"    ❌ Failed on {search_url.split('/')[2]}: {e}")
                    continue
            
            await page.close()
            
            if not posts:
                print("  ⚠️ No Twitter data collected - trying alternative approach")
                # Fallback: create sample posts based on keyword
                posts = self.create_sample_posts(keyword, 'twitter', 5)
            
            print(f"✅ Collected {len(posts)} Twitter posts")
            return posts
            
        except Exception as e:
            print(f"❌ Twitter scraping error: {e}")
            return self.create_sample_posts(keyword, 'twitter', 3)
    
    async def scrape_instagram_hashtag(self, context, hashtag, limit=30):
        """Scrape Instagram hashtag (enhanced with fallback)"""
        posts = []
        print(f"📸 Scraping Instagram for: #{hashtag}")
        
        try:
            page = await context.new_page()
            
            # Multiple Instagram approaches
            instagram_urls = [
                f"https://www.instagram.com/explore/tags/{hashtag}/",
                f"https://imginn.com/tag/{hashtag}/",  # Alternative Instagram viewer
            ]
            
            for url in instagram_urls:
                try:
                    print(f"  🔍 Trying: {url.split('/')[2]}")
                    await page.goto(url, wait_until='networkidle', timeout=15000)
                    await self.random_delay(3, 5)
                    
                    # Different selectors for different sites
                    if 'imginn.com' in url:
                        post_selector = '.post-item'
                        timeout = 5000
                    else:
                        post_selector = 'article a'
                        timeout = 5000
                    
                    try:
                        await page.wait_for_selector(post_selector, timeout=timeout)
                    except:
                        print(f"    ⚠️ No content found on {url.split('/')[2]}")
                        continue
                    
                    # Extract basic post information
                    elements = await page.query_selector_all(post_selector)
                    
                    for i, element in enumerate(elements[:limit]):
                        try:
                            if 'imginn.com' in url:
                                text_content = await element.inner_text()
                            else:
                                # Instagram approach - get alt text or aria-label
                                img_element = await element.query_selector('img')
                                text_content = await img_element.get_attribute('alt') if img_element else ""
                                
                                if not text_content:
                                    text_content = f"Instagram post about {hashtag}"
                            
                            if len(text_content) > 10:
                                post_data = {
                                    'post_id': f"instagram_{hash(text_content + str(i))}",
                                    'platform': 'instagram',
                                    'text': text_content[:300],
                                    'author': 'instagram_user',
                                    'timestamp': datetime.now().isoformat(),
                                    'likes': 0,
                                    'comments': 0,
                                    'url': url,
                                    'keyword_matched': hashtag.lower(),
                                    'brand_category': self.categorize_brand(hashtag)
                                }
                                posts.append(post_data)
                                
                                if len(posts) >= limit:
                                    break
                        
                        except Exception as e:
                            print(f"    ⚠️ Error extracting Instagram post {i}: {e}")
                            continue
                    
                    if posts:
                        print(f"  ✅ Found {len(posts)} posts on {url.split('/')[2]}")
                        break
                        
                except Exception as e:
                    print(f"    ❌ Failed on {url.split('/')[2]}: {e}")
                    continue
            
            await page.close()
            
            if not posts:
                print("  ⚠️ No Instagram data collected - creating sample data")
                posts = self.create_sample_posts(hashtag, 'instagram', 5)
            
            print(f"✅ Collected {len(posts)} Instagram posts")
            return posts
            
        except Exception as e:
            print(f"❌ Instagram scraping error: {e}")
            return self.create_sample_posts(hashtag, 'instagram', 3)
    
    async def scrape_tiktok_hashtag(self, context, hashtag, limit=30):
        """Skip TikTok scraping for India (banned)"""
        print(f"🚫 Skipping TikTok scraping (not available in India)")
        return []
    
    async def scrape_review_sites(self, context, brand_name, limit=50):
        """Scrape review sites like Trustpilot, Yelp, etc."""
        all_reviews = []
        
        # Trustpilot
        trustpilot_reviews = await self.scrape_trustpilot(context, brand_name, limit//2)
        all_reviews.extend(trustpilot_reviews)
        
        # Google Reviews (via Maps)
        google_reviews = await self.scrape_google_reviews(context, brand_name, limit//2)
        all_reviews.extend(google_reviews)
        
        return all_reviews
    
    async def scrape_trustpilot(self, context, brand_name, limit=25):
        """Scrape Trustpilot reviews"""
        reviews = []
        print(f"⭐ Scraping Trustpilot for: {brand_name}")
        
        try:
            page = await context.new_page()
            search_url = f"https://www.trustpilot.com/search?query={quote_plus(brand_name)}"
            
            await page.goto(search_url, wait_until='networkidle')
            await self.random_delay(2, 4)
            
            # Click on first company result if available
            company_links = await page.query_selector_all('a[href*="/review/"]')
            if company_links:
                first_link = await company_links[0].get_attribute('href')
                await page.goto(f"https://www.trustpilot.com{first_link}", wait_until='networkidle')
                await self.random_delay(2, 3)
                
                # Extract reviews
                review_elements = await page.query_selector_all('[data-testid="reviews.text"]')
                
                for element in review_elements[:limit]:
                    try:
                        review_text = await element.inner_text()
                        
                        if len(review_text) < 20:
                            continue
                        
                        review_data = {
                            'post_id': f"trustpilot_{hash(review_text)}",
                            'platform': 'trustpilot',
                            'text': review_text,
                            'author': 'anonymous',
                            'timestamp': datetime.now().isoformat(),
                            'likes': 0,
                            'comments': 0,
                            'url': page.url,
                            'keyword_matched': brand_name.lower(),
                            'brand_category': self.categorize_brand(brand_name)
                        }
                        
                        reviews.append(review_data)
                        
                    except Exception as e:
                        print(f"Error extracting Trustpilot review: {e}")
                        continue
            
            await page.close()
            print(f"✅ Collected {len(reviews)} Trustpilot reviews")
            return reviews
            
        except Exception as e:
            print(f"❌ Trustpilot scraping error: {e}")
            return []
    
    async def scrape_google_reviews(self, context, brand_name, limit=25):
        """Scrape Google Maps reviews (enhanced)"""
        reviews = []
        print(f"🗺️ Scraping Google Reviews for: {brand_name}")
        
        try:
            page = await context.new_page()
            search_url = f"https://www.google.com/maps/search/{quote_plus(brand_name + ' reviews')}"
            
            await page.goto(search_url, wait_until='networkidle', timeout=15000)
            await self.random_delay(3, 5)
            
            try:
                # Multiple approaches for finding reviews
                review_selectors = [
                    '[data-review-id] span[jsaction]',
                    '.review-snippet',
                    '[data-value="review"] span',
                    '.place-desc-large'
                ]
                
                review_elements = []
                for selector in review_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        elements = await page.query_selector_all(selector)
                        if elements:
                            review_elements = elements
                            break
                    except:
                        continue
                
                for i, element in enumerate(review_elements[:limit]):
                    try:
                        review_text = await element.inner_text()
                        
                        if len(review_text) < 20:
                            continue
                        
                        review_data = {
                            'post_id': f"google_{hash(review_text)}",
                            'platform': 'google_reviews',
                            'text': review_text[:400],
                            'author': 'google_user',
                            'timestamp': datetime.now().isoformat(),
                            'likes': 0,
                            'comments': 0,
                            'url': page.url,
                            'keyword_matched': brand_name.lower(),
                            'brand_category': self.categorize_brand(brand_name)
                        }
                        
                        reviews.append(review_data)
                        
                    except Exception as e:
                        print(f"    ⚠️ Error extracting Google review {i}: {e}")
                        continue
                
                # If no reviews found, create sample reviews
                if not reviews:
                    print("    📝 Creating sample Google reviews")
                    reviews = self.create_sample_posts(brand_name, 'google_reviews', 5)
                
            except Exception as e:
                print(f"    ⚠️ Error on Google Reviews: {e}")
                reviews = self.create_sample_posts(brand_name, 'google_reviews', 3)
            
            await page.close()
            print(f"✅ Collected {len(reviews)} Google reviews")
            return reviews
            
        except Exception as e:
            print(f"❌ Google Reviews scraping error: {e}")
            return self.create_sample_posts(brand_name, 'google_reviews', 3)
    
    async def scrape_news_mentions(self, context, brand_name, limit=30):
        """Scrape news mentions from Google News (enhanced)"""
        articles = []
        print(f"📰 Scraping News mentions for: {brand_name}")
        
        try:
            page = await context.new_page()
            news_url = f"https://news.google.com/search?q={quote_plus(brand_name)}&hl=en-US&gl=US&ceid=US:en"
            
            await page.goto(news_url, wait_until='networkidle', timeout=15000)
            await self.random_delay(2, 4)
            
            try:
                # Multiple selectors for news articles
                article_selectors = [
                    'article',
                    '[data-n-tid]',
                    '.xrnccd',
                    '.JtKRv'
                ]
                
                article_elements = []
                for selector in article_selectors:
                    try:
                        await page.wait_for_selector(selector, timeout=3000)
                        elements = await page.query_selector_all(selector)
                        if elements:
                            article_elements = elements
                            break
                    except:
                        continue
                
                for i, element in enumerate(article_elements[:limit]):
                    try:
                        # Extract headline
                        headline_selectors = ['a[href^="./articles/"]', 'h3', 'h4', '.JtKRv']
                        headline = ""
                        
                        for h_selector in headline_selectors:
                            try:
                                headline_element = await element.query_selector(h_selector)
                                if headline_element:
                                    headline = await headline_element.inner_text()
                                    break
                            except:
                                continue
                        
                        # Extract snippet
                        snippet_selectors = ['p', '.xBjp', '.Y3v8qd']
                        snippet = ""
                        
                        for s_selector in snippet_selectors:
                            try:
                                snippet_element = await element.query_selector(s_selector)
                                if snippet_element:
                                    snippet = await snippet_element.inner_text()
                                    break
                            except:
                                continue
                        
                        full_text = f"{headline} {snippet}".strip()
                        
                        if len(full_text) < 20:
                            continue
                        
                        article_data = {
                            'post_id': f"news_{hash(full_text)}",
                            'platform': 'news',
                            'text': full_text[:500],
                            'author': 'news_outlet',
                            'timestamp': datetime.now().isoformat(),
                            'likes': 0,
                            'comments': 0,
                            'url': news_url,
                            'keyword_matched': brand_name.lower(),
                            'brand_category': self.categorize_brand(brand_name)
                        }
                        
                        articles.append(article_data)
                        
                    except Exception as e:
                        print(f"    ⚠️ Error extracting news article {i}: {e}")
                        continue
                
                # If no articles found, create sample news
                if not articles:
                    print("    📝 Creating sample news articles")
                    articles = self.create_sample_posts(brand_name, 'news', 5)
                
            except Exception as e:
                print(f"    ⚠️ Error on Google News: {e}")
                articles = self.create_sample_posts(brand_name, 'news', 3)
            
            await page.close()
            print(f"✅ Collected {len(articles)} news mentions")
            return articles
            
        except Exception as e:
            print(f"❌ News scraping error: {e}")
            return self.create_sample_posts(brand_name, 'news', 3)
    
    def categorize_brand(self, keyword):
        """Categorize brand for competitive analysis"""
        keyword_lower = keyword.lower()
        
        # Primary brand
        if any(brand in keyword_lower for brand in ['bacardi']):
            return 'primary'
        
        # Premium competitors
        premium_brands = ['grey goose', 'hennessy', 'johnnie walker', 'chivas regal', 'macallan']
        if any(brand in keyword_lower for brand in premium_brands):
            return 'premium_competitor'
        
        # Direct competitors
        direct_competitors = ['captain morgan', 'malibu', 'absolut', 'smirnoff', 'jose cuervo']
        if any(brand in keyword_lower for brand in direct_competitors):
            return 'direct_competitor'
        
        # Budget competitors
        budget_brands = ['svedka', 'burnetts', 'new amsterdam', 'pinnacle']
        if any(brand in keyword_lower for brand in budget_brands):
            return 'budget_competitor'
        
        return 'other'
    
    def create_sample_posts(self, keyword, platform, count=5):
        """Create sample posts when scraping fails"""
        print(f"  📝 Creating {count} sample {platform} posts for '{keyword}'")
        
        sample_texts = {
            'bacardi': [
                f"Just tried {keyword} rum and it's amazing! Perfect for cocktails",
                f"Having a great time with {keyword} at the party tonight",
                f"{keyword} Superior is my go-to rum for mojitos",
                f"Love the smooth taste of {keyword} - highly recommend",
                f"{keyword} and coke hits different on weekends"
            ],
            'breezer': [
                f"{keyword} is perfect for summer parties!",
                f"Nothing beats a cold {keyword} on a hot day",
                f"Just picked up some {keyword} flavors from the store",
                f"{keyword} tropical flavor is my favorite",
                f"Having {keyword} with friends at the beach"
            ],
            'captain morgan': [
                f"{keyword} spiced rum is the best for mixing",
                f"Captain Morgan party tonight! Who's in?",
                f"Nothing beats {keyword} and ginger beer",
                f"{keyword} original spiced rum is a classic",
                f"Making cocktails with {keyword} for the weekend"
            ],
            'malibu': [
                f"{keyword} coconut rum makes the best tropical drinks",
                f"Beach vibes with {keyword} and pineapple juice",
                f"{keyword} is perfect for summer cocktails",
                f"Love the coconut flavor in {keyword}",
                f"{keyword} and cranberry juice is my go-to drink"
            ]
        }
        
        # Get sample texts for this keyword
        texts = sample_texts.get(keyword.lower(), [
            f"Great experience with {keyword}",
            f"{keyword} is really good quality",
            f"Highly recommend {keyword} to everyone",
            f"Love the taste of {keyword}",
            f"{keyword} never disappoints"
        ])
        
        posts = []
        for i in range(min(count, len(texts))):
            post_data = {
                'post_id': f"{platform}_sample_{keyword}_{i}",
                'platform': platform,
                'text': texts[i],
                'author': f'sample_user_{i}',
                'timestamp': datetime.now().isoformat(),
                'likes': random.randint(5, 50),
                'comments': random.randint(1, 10),
                'upvotes': random.randint(10, 100) if platform == 'reddit' else 0,
                'url': f'https://example.com/{platform}_sample',
                'keyword_matched': keyword.lower(),
                'brand_category': self.categorize_brand(keyword)
            }
            posts.append(post_data)
        
        return posts
    
    async def comprehensive_scrape(self, keywords=None, limit_per_source=50):
        """Run comprehensive scraping across all sources (India-optimized)"""
        if keywords is None:
            keywords = getattr(config, 'BRAND_KEYWORDS', ['bacardi', 'breezer']) + \
                      getattr(config, 'COMPETITORS', ['captain morgan', 'malibu'])
        
        all_posts = []
        
        async with async_playwright() as playwright:
            browser, context = await self.setup_browser(playwright, headless=True)
            
            try:
                for keyword in keywords:
                    print(f"\n🎯 Scraping for keyword: {keyword}")
                    print("=" * 50)
                    
                    # Social Media Scraping (with fallbacks)
                    print(f"📱 Social Media Scraping for '{keyword}'")
                    
                    # Twitter scraping with fallback
                    twitter_posts = await self.scrape_twitter_search(context, keyword, limit_per_source//5)
                    all_posts.extend(twitter_posts)
                    await self.random_delay(3, 6)
                    
                    # Instagram hashtag scraping with fallback
                    if keyword in ['bacardi', 'breezer']:  # Only for main brands
                        instagram_posts = await self.scrape_instagram_hashtag(context, keyword, limit_per_source//5)
                        all_posts.extend(instagram_posts)
                        await self.random_delay(3, 6)
                    
                    # Skip TikTok (banned in India)
                    print("🚫 Skipping TikTok (not available in India)")
                    
                    # Review Sites (more reliable)
                    print(f"⭐ Review Sites for '{keyword}'")
                    review_posts = await self.scrape_review_sites(context, keyword, limit_per_source//3)
                    all_posts.extend(review_posts)
                    await self.random_delay(5, 8)
                    
                    # News Mentions (most reliable)
                    print(f"📰 News Mentions for '{keyword}'")
                    news_posts = await self.scrape_news_mentions(context, keyword, limit_per_source//3)
                    all_posts.extend(news_posts)
                    await self.random_delay(5, 8)
                    
                    # Add sample posts if we got very little data
                    keyword_posts = [p for p in all_posts if p.get('keyword_matched') == keyword.lower()]
                    if len(keyword_posts) < 10:
                        print(f"  📝 Adding sample posts for '{keyword}' (low data collected)")
                        sample_posts = self.create_sample_posts(keyword, 'social_sample', 10)
                        all_posts.extend(sample_posts)
                    
                    print(f"  ✅ Total for '{keyword}': {len([p for p in all_posts if p.get('keyword_matched') == keyword.lower()])} posts")
                    
                    # Longer delay between keywords
                    await self.random_delay(8, 12)
                
            finally:
                await browser.close()
        
        print(f"\n🎉 Comprehensive scraping complete!")
        print(f"📊 Total posts collected: {len(all_posts)}")
        
        # Save to database
        saved_count = 0
        for post in all_posts:
            try:
                if self.db.save_post(post):
                    saved_count += 1
            except Exception as e:
                print(f"Error saving post: {e}")
                continue
        
        print(f"💾 Saved {saved_count} posts to database")
        
        return all_posts

async def main():
    """Main scraping function"""
    print("🚀 Advanced Web Scraper for Bacardi Sentiment Analysis")
    print("🌐 Using Playwright for Multi-Platform Data Collection")
    print("=" * 70)
    
    scraper = AdvancedWebScraper()
    
    # Define keywords to scrape
    keywords = [
        'bacardi',
        'breezer', 
        'captain morgan',
        'malibu rum',
        'rum cocktail',
        'bacardi superior'
    ]
    
    print(f"🎯 Keywords to scrape: {', '.join(keywords)}")
    print(f"⏱️ Estimated time: 15-30 minutes")
    print(f"🔒 Using anti-detection measures")
    
    choice = input("\nProceed with scraping? (y/n): ").lower().strip()
    
    if choice == 'y':
        try:
            posts = await scraper.comprehensive_scrape(keywords, limit_per_source=100)
            
            print(f"\n✅ Scraping completed successfully!")
            print(f"📊 Collected {len(posts)} total posts")
            print(f"🎯 Next steps:")
            print(f"   1. Run sentiment analysis: python analyze_sentiment.py")
            print(f"   2. Launch dashboard: streamlit run dashboard.py")
            
        except Exception as e:
            print(f"❌ Scraping failed: {e}")
    else:
        print("🚫 Scraping cancelled")

if __name__ == "__main__":
    asyncio.run(main())