# Brand keywords to track
BRAND_KEYWORDS = [
    'bacardi', 
    'breezer', 
    'bacardi rum', 
    'white rum bacardi',
    'bacardi superior', 
    'bacardi gold'
]

# Hashtags to monitor
HASHTAGS = [
    '#bacardi', 
    '#breezer', 
    '#bacardirum', 
    '#rumlife',
    '#bacardisuperior'
]

# Competitor keywords (optional)
COMPETITORS = [
    'captain morgan', 
    'malibu', 
    'havana club',
    'kraken rum'
]

# Try to import API keys from local config file
try:
    from config_local import *
    print("✅ API keys loaded from config_local.py")
except ImportError:
    print("⚠️ config_local.py not found. Please create it with your API keys.")
    TWITTER_BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAALTG2gEAAAAAdpvJK%2BKR%2BwBYLoe%2B9Dfaj1DjtaE%3DxtNjXVF0z9ZzZfIVZwUkqdYK4kHnInU3w4YuRiIn4KHbiRdFJ0"
    TWITTER_API_KEY = "cpvwBrPTduKoHWaJrRGeGpgf8"
    TWITTER_API_SECRET = "UKESHeOBX6bfnET72x4gel9BgHTTN1aFWIACSoQ6e9yOu0GJfT"
    TWITTER_ACCESS_TOKEN = "1937024198469369856-w0av1C4l7LQWY5fWBhGgLRxlZbCZJS"
    TWITTER_ACCESS_TOKEN_SECRET = "fNCCAMSWk9m1Sto6PeHwcrzfZ0JxDevm4EhmXUMHvHjsu"
    
    REDDIT_CLIENT_ID = "aAwa29mpNMRzQKtgkfebQw"
    REDDIT_CLIENT_SECRET = "TMPXj33kr77IsgGDnoWL1rADnCRAAw"
    REDDIT_USERNAME = "Low-Iron-2783"
    REDDIT_PASSWORD = "uZD2.aBXFsb)B=/"

# Sentiment analysis settings
SENTIMENT_THRESHOLDS = {
    'positive': 0.1,
    'negative': -0.1
}

# Collection settings
DEFAULT_TWEET_LIMIT = 100
DEFAULT_REDDIT_LIMIT = 50
RATE_LIMIT_DELAY = 1  # seconds between requests