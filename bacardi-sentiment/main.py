import subprocess
import sys

def main():
    print("🍹 Bacardi Sentiment Analysis POC")
    print("=" * 40)
    
    choice = input("""
    Choose an option:
    1. Run data collection
    2. Launch dashboard
    3. Exit
    
    Enter choice (1-3): """)
    
    if choice == "1":
        from data_collector import SocialMediaCollector
        from sentiment_analyzer import SentimentAnalyzer
        from database import DatabaseManager
        
        collector = SocialMediaCollector()
        analyzer = SentimentAnalyzer()
        db = DatabaseManager()
        
        print("Collecting data...")
        # Run collection logic
        
    elif choice == "2":
        print("Launching dashboard...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", "dashboard.py"])
    
    elif choice == "3":
        print("Goodbye!")
        sys.exit()

if __name__ == "__main__":
    main()