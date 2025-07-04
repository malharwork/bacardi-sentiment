import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("🚀 Bacardi Sentiment Analysis Setup")
    print("=" * 40)
    
    # Check Python version
    print(f"🐍 Python version: {sys.version}")
    if sys.version_info < (3, 7):
        print("❌ Python 3.7+ required")
        return
    
    # Install requirements
    if not run_command("pip install -r requirements.txt", "Installing Python packages"):
        return
    
    # Install Playwright browsers
    if not run_command("playwright install", "Installing Playwright browsers"):
        print("⚠️ Playwright browser installation failed")
        print("💡 Try running: python -m playwright install")
        return
    
    # Create data directory
    os.makedirs("data", exist_ok=True)
    print("✅ Created data directory")
    
    # Initialize database
    try:
        from database import DatabaseManager
        db = DatabaseManager()
        print("✅ Database initialized")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return
    
    # Run migration if needed
    try:
        from migrate_database import migrate_database
        migrate_database()
        print("✅ Database migration completed")
    except Exception as e:
        print(f"⚠️ Database migration: {e}")
    
    print(f"\n🎉 Setup completed successfully!")
    print(f"\n🎯 Next steps:")
    print(f"1. Update config_local.py with your API keys")
    print(f"2. Run data collection: python enhanced_data_collector.py")
    print(f"3. Analyze sentiment: python analyze_sentiment.py")
    print(f"4. Launch dashboard: streamlit run dashboard.py")
    
    # Test basic functionality
    print(f"\n🧪 Running basic tests...")
    
    # Test imports
    try:
        import playwright
        import textblob
        import vaderSentiment
        import streamlit
        import plotly
        print("✅ All key libraries imported successfully")
    except ImportError as e:
        print(f"❌ Import test failed: {e}")
        return
    
    print(f"\n✅ Setup verification complete!")

if __name__ == "__main__":
    main()