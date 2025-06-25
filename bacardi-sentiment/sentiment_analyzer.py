from textblob import TextBlob
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

class SentimentAnalyzer:
    def __init__(self):
        self.vader = SentimentIntensityAnalyzer()
    
    def clean_text(self, text):
        """Basic text cleaning"""
        text = re.sub(r'http\S+', '', text)  # Remove URLs
        text = re.sub(r'@\w+', '', text)     # Remove mentions
        text = re.sub(r'#\w+', '', text)     # Remove hashtags
        return text.strip()
    
    def analyze_sentiment(self, text):
        """Analyze sentiment using both TextBlob and VADER"""
        cleaned_text = self.clean_text(text)
        
        # TextBlob analysis
        blob = TextBlob(cleaned_text)
        textblob_polarity = blob.sentiment.polarity
        
        # VADER analysis
        vader_scores = self.vader.polarity_scores(cleaned_text)
        
        # Combine scores (simple average)
        combined_score = (textblob_polarity + vader_scores['compound']) / 2
        
        # Classify sentiment
        if combined_score >= 0.1:
            sentiment_label = 'positive'
        elif combined_score <= -0.1:
            sentiment_label = 'negative'
        else:
            sentiment_label = 'neutral'
        
        return {
            'sentiment_score': combined_score,
            'sentiment_label': sentiment_label,
            'confidence': abs(combined_score),
            'textblob_score': textblob_polarity,
            'vader_score': vader_scores['compound']
        }