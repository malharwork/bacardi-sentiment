import tweepy

# Put your bearer token directly here for testing
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAALTG2gEAAAAAdpvJK%2BKR%2BwBYLoe%2B9Dfaj1DjtaE%3DxtNjXVF0z9ZzZfIVZwUkqdYK4kHnInU3w4YuRiIn4KHbiRdFJ0"

try:
    client = tweepy.Client(bearer_token=BEARER_TOKEN)
    
    # Try a simple search
    response = client.search_recent_tweets(query="test", max_results=10)
    print("✅ Twitter API working!")
    print(f"Found {len(response.data) if response.data else 0} tweets")
    
except Exception as e:
    print(f"❌ Error: {e}")