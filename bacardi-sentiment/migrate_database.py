import sqlite3
import os

def migrate_database(db_path="data/bacardi_posts.db"):
    """Add missing columns to existing database"""
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        print("Run the data collector first to create the database.")
        return False
    
    print(f"🔄 Migrating database: {db_path}")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get existing columns
        cursor.execute("PRAGMA table_info(social_posts)")
        existing_columns = [column[1] for column in cursor.fetchall()]
        
        print(f"📋 Existing columns: {', '.join(existing_columns)}")
        
        # Define new columns that might be missing
        new_columns = [
            ('url', 'TEXT'),
            ('keyword_matched', 'TEXT'),
            ('brand_category', 'TEXT'),
            ('subreddit', 'TEXT'),
            ('video_id', 'TEXT'),
            ('verified', 'BOOLEAN DEFAULT 0'),
            ('upvotes', 'INTEGER DEFAULT 0'),
            ('engagement_score', 'REAL'),
            ('confidence_score', 'REAL')
        ]
        
        added_columns = []
        
        # Add missing columns
        for column_name, column_type in new_columns:
            if column_name not in existing_columns:
                try:
                    cursor.execute(f'ALTER TABLE social_posts ADD COLUMN {column_name} {column_type}')
                    added_columns.append(column_name)
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"❌ Error adding column {column_name}: {e}")
        
        if added_columns:
            conn.commit()
            print(f"\n🎉 Migration complete! Added {len(added_columns)} columns:")
            for col in added_columns:
                print(f"   - {col}")
        else:
            print("✅ No migration needed - all columns already exist!")
        
        # Verify final schema
        cursor.execute("PRAGMA table_info(social_posts)")
        final_columns = [column[1] for column in cursor.fetchall()]
        
        print(f"\n📊 Final schema ({len(final_columns)} columns):")
        for col in sorted(final_columns):
            print(f"   - {col}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Bacardi Sentiment Database Migration")
    print("=" * 50)
    
    # Default database path
    db_path = "data/bacardi_posts.db"
    
    # Check if custom path provided
    import sys
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    
    success = migrate_database(db_path)
    
    if success:
        print(f"\n🎯 Next steps:")
        print(f"1. Run data collector: python data_collector.py")
        print(f"2. Run sentiment analysis: python analyze_sentiment.py")
        print(f"3. Launch dashboard: streamlit run dashboard.py")
    else:
        print(f"\n❌ Migration failed. Please check the error messages above.")

if __name__ == "__main__":
    main()