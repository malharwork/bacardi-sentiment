import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlite3
from datetime import datetime, timedelta
import time

# Page config
st.set_page_config(
    page_title="Bacardi Historical Sentiment Dashboard",
    page_icon="🥃",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #2E8B57;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .positive-sentiment {
        background-color: #d4edda;
        border-left: 5px solid #2E8B57;
        padding: 10px;
        margin: 10px 0;
    }
    .negative-sentiment {
        background-color: #f8d7da;
        border-left: 5px solid #DC143C;
        padding: 10px;
        margin: 10px 0;
    }
    .neutral-sentiment {
        background-color: #e2e3e5;
        border-left: 5px solid #708090;
        padding: 10px;
        margin: 10px 0;
    }
    .year-stats {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        margin: 10px 5px;
        border: none;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        min-height: 160px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    .year-stats h3 {
        font-size: 2rem;
        font-weight: bold;
        margin: 0 0 10px 0;
        color: white;
    }
    .year-stats p {
        margin: 5px 0;
        font-size: 0.9rem;
        color: rgba(255, 255, 255, 0.9);
    }
    .year-stats strong {
        color: white;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Initialize database connection
@st.cache_resource
def init_database():
    try:
        from database import DatabaseManager
        return DatabaseManager()
    except ImportError:
        st.error("❌ Database module not found. Please ensure database.py exists.")
        return None

def get_engagement_formula(conn):
    """Build engagement calculation based on available columns"""
    column_check = conn.execute("PRAGMA table_info(social_posts)").fetchall()
    column_names = [col[1] for col in column_check]
    
    engagement_calc = []
    if 'likes' in column_names:
        engagement_calc.append('COALESCE(likes, 0)')
    if 'upvotes' in column_names:
        engagement_calc.append('COALESCE(upvotes, 0)')
    if 'comments' in column_names:
        engagement_calc.append('COALESCE(comments, 0)')
    if 'retweets' in column_names:
        engagement_calc.append('COALESCE(retweets, 0)')
    if 'engagement_score' in column_names:
        return 'COALESCE(engagement_score, 0)'
    
    if engagement_calc:
        return ' + '.join(engagement_calc)
    else:
        return '0'

def main():
    st.markdown('<h1 class="main-header">🥃 Bacardi Sentiment Analysis Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("**Multi-Platform Analysis:** Reddit • YouTube • News • Reviews • Trustpilot")
    
    # Initialize database
    db = init_database()
    if not db:
        st.stop()
    
    # Sidebar controls
    st.sidebar.header("📊 Dashboard Controls")
    
    # Auto-refresh toggle
    auto_refresh = st.sidebar.checkbox("🔄 Auto-refresh (30s)", value=False)
    
    # Manual refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Sentiment Analysis Status
    st.sidebar.subheader("🧠 Sentiment Analysis Status")
    try:
        conn = sqlite3.connect(db.db_path)
        
        analysis_query = '''
        SELECT 
            COUNT(*) as total_posts,
            SUM(CASE WHEN sentiment_label IS NOT NULL THEN 1 ELSE 0 END) as analyzed_posts
        FROM social_posts
        '''
        
        analysis_df = pd.read_sql_query(analysis_query, conn)
        conn.close()
        
        if not analysis_df.empty:
            total = int(analysis_df.iloc[0]['total_posts'])
            analyzed = int(analysis_df.iloc[0]['analyzed_posts'])
            unanalyzed = total - analyzed
            progress = (analyzed / total * 100) if total > 0 else 0
            
            st.sidebar.metric("Analyzed Posts", f"{analyzed:,} / {total:,}")
            st.sidebar.progress(progress / 100)
            st.sidebar.caption(f"{progress:.1f}% complete")
            
            if unanalyzed > 0:
                st.sidebar.warning(f"⚠️ {unanalyzed:,} posts need analysis")
                st.sidebar.info("Run: python analyze_sentiment.py")
            else:
                st.sidebar.success("✅ All posts analyzed!")
        
    except Exception as e:
        st.sidebar.error(f"Error checking analysis status: {e}")
    
    # Time period filter
    st.sidebar.subheader("📅 Time Period")
    date_range = st.sidebar.selectbox(
        "Select time period:",
        ["All time", "Last 2 years", "Last 1 year", "Last 6 months", "Last 3 months", "Last 30 days"],
        index=0
    )
    
    # Platform filter
    st.sidebar.subheader("🔧 Platform Filter")
    available_platforms = ["All", "reddit", "youtube", "facebook", "news", "reviews", "trustpilot", "google_reviews"]
    selected_platform = st.sidebar.selectbox("Select platform:", available_platforms)
    
    # Brand Category filter
    st.sidebar.subheader("🏢 Brand Filter")
    brand_categories = ["All", "primary", "direct_competitor", "premium_competitor", "budget_competitor", "general", "other"]
    selected_brand = st.sidebar.selectbox("Select brand category:", brand_categories)
    
    # Sentiment filter
    st.sidebar.subheader("😊 Sentiment Filter")
    sentiment_filter = st.sidebar.selectbox("Select sentiment:", ["All", "positive", "negative", "neutral"])
    
    # Advanced filters
    st.sidebar.subheader("🔍 Advanced Filters")
    min_engagement = st.sidebar.slider("Minimum engagement:", 0, 100, 0)
    show_verified_only = st.sidebar.checkbox("Verified authors only", value=False)
    
    # Platform colors
    platform_colors = {
        'reddit': '#FF4500',
        'youtube': '#FF0000', 
        'facebook': '#1877F2',
        'instagram': '#E4405F'
    }
    
    # Brand category colors
    brand_colors = {
        'primary': '#2E8B57',
        'direct_competitor': '#DC143C',
        'premium_competitor': '#9932CC',
        'budget_competitor': '#FF8C00',
        'general': '#708090',
        'other': '#A9A9A9'
    }
    
    # Sentiment colors
    sentiment_colors = {
        'positive': '#2E8B57',
        'negative': '#DC143C',
        'neutral': '#708090'
    }
    
    # Auto-refresh logic
    if auto_refresh:
        time.sleep(30)
        st.rerun()
    
    # Build filters based on selections
    def build_filters():
        filters = ["1=1"]  # Always true condition
        
        # Date filter
        if date_range == "Last 2 years":
            filters.append("timestamp >= datetime('now', '-2 years')")
        elif date_range == "Last 1 year":
            filters.append("timestamp >= datetime('now', '-1 year')")
        elif date_range == "Last 6 months":
            filters.append("timestamp >= datetime('now', '-6 months')")
        elif date_range == "Last 3 months":
            filters.append("timestamp >= datetime('now', '-3 months')")
        elif date_range == "Last 30 days":
            filters.append("timestamp >= datetime('now', '-30 days')")
        
        # Platform filter
        if selected_platform != "All":
            filters.append(f"platform = '{selected_platform}'")
        
        # Brand filter
        if selected_brand != "All":
            filters.append(f"brand_category = '{selected_brand}'")
        
        # Sentiment filter
        if sentiment_filter != "All":
            filters.append(f"sentiment_label = '{sentiment_filter}'")
        
        # Engagement filter
        if min_engagement > 0:
            conn_temp = sqlite3.connect(db.db_path)
            engagement_formula = get_engagement_formula(conn_temp)
            conn_temp.close()
            filters.append(f"({engagement_formula}) >= {min_engagement}")
        
        # Verified filter
        if show_verified_only:
            filters.append("verified = 1")
        
        return " AND ".join(filters)
    
    filter_clause = build_filters()
    
    # Main dashboard content
    try:
        conn = sqlite3.connect(db.db_path)
        engagement_formula = get_engagement_formula(conn)
        
        # Overall metrics
        metrics_query = f'''
        SELECT 
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as total_posts,
            SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
            MIN(timestamp) as earliest_post,
            MAX(timestamp) as latest_post,
            COUNT(DISTINCT platform) as platforms_covered,
            COUNT(DISTINCT brand_category) as brand_categories,
            AVG({engagement_formula}) as avg_engagement
        FROM social_posts 
        WHERE {filter_clause}
        '''
        
        stats_df = pd.read_sql_query(metrics_query, conn)
        stats = stats_df.iloc[0] if not stats_df.empty and stats_df.iloc[0]['total_posts'] > 0 else None
        
        if stats is None or stats['total_posts'] == 0:
            st.warning("⚠️ No data available for the selected filters.")
            st.info("Try adjusting your filters or run the data collector to gather more data.")
            conn.close()
            return
        
        # Display key metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "📊 Total Posts", 
                f"{int(stats['total_posts']):,}",
                help="Total posts analyzed across all selected filters"
            )
        
        with col2:
            avg_sentiment = float(stats['avg_sentiment']) if stats['avg_sentiment'] else 0
            sentiment_emoji = "😊" if avg_sentiment > 0.1 else "😐" if avg_sentiment > -0.1 else "😞"
            st.metric(
                "📈 Avg Sentiment", 
                f"{avg_sentiment:.3f} {sentiment_emoji}",
                help="Average sentiment score (-1 to +1)"
            )
        
        with col3:
            positive_pct = (stats['positive_count'] / stats['total_posts']) * 100 if stats['total_posts'] > 0 else 0
            st.metric(
                "✅ Positive %", 
                f"{positive_pct:.1f}%",
                help="Percentage of posts with positive sentiment"
            )
        
        with col4:
            st.metric(
                "🌐 Platforms", 
                "5",
                help="Number of platforms with data (Reddit, YouTube, News, Reviews, Trustpilot)"
            )
        
        with col5:
            avg_engagement = float(stats['avg_engagement']) if stats['avg_engagement'] else 0
            st.metric(
                "👍 Avg Engagement", 
                f"{avg_engagement:.1f}",
                help="Average engagement score across posts"
            )
        
        # Row 2: Key Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Sentiment Distribution")
            
            dist_query = f'''
            SELECT 
                sentiment_label,
                COUNT(*) as count
            FROM social_posts 
            WHERE {filter_clause} AND sentiment_label IS NOT NULL
            GROUP BY sentiment_label
            '''
            
            dist_df = pd.read_sql_query(dist_query, conn)
            
            if not dist_df.empty:
                fig = px.pie(
                    dist_df, 
                    values='count', 
                    names='sentiment_label',
                    title="Overall Sentiment Breakdown",
                    color='sentiment_label',
                    color_discrete_map=sentiment_colors
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(showlegend=True, height=400)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No sentiment data available for selected filters.")
        
        with col2:
            st.subheader("📱 Platform Breakdown")
            
            platform_query = f'''
            SELECT 
                platform,
                COUNT(*) as post_count,
                AVG(sentiment_score) as avg_sentiment,
                SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count
            FROM social_posts 
            WHERE {filter_clause}
            AND platform NOT IN ('instagram', 'twitter')
            GROUP BY platform
            ORDER BY post_count DESC
            '''
            
            platform_df = pd.read_sql_query(platform_query, conn)
            
            if not platform_df.empty:
                fig = px.bar(
                    platform_df, 
                    x='post_count', 
                    y='platform',
                    orientation='h',
                    title="Posts by Platform (Excluding Instagram & Twitter)",
                    color='avg_sentiment',
                    color_continuous_scale='RdYlGn',
                    hover_data=['positive_count', 'negative_count']
                )
                fig.update_layout(yaxis_title="Platform", xaxis_title="Post Count", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                # Add info about excluded platforms
                st.info("📝 Instagram and Twitter are excluded from this chart due to data collection limitations")
            else:
                st.info("No platform data available for selected filters (excluding Instagram & Twitter).")
        
        # Brand Category Analysis
        st.subheader("🏢 Brand Category Analysis")
        
        brand_query = f'''
        SELECT 
            brand_category,
            COUNT(*) as post_count,
            AVG(sentiment_score) as avg_sentiment,
            SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
            AVG({engagement_formula}) as avg_engagement
        FROM social_posts 
        WHERE {filter_clause} AND brand_category IS NOT NULL 
        AND brand_category != 'general'
        GROUP BY brand_category
        ORDER BY post_count DESC
        '''
        
        brand_df = pd.read_sql_query(brand_query, conn)
        
        if not brand_df.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.bar(
                    brand_df,
                    x='brand_category',
                    y='post_count',
                    title="Posts by Brand Category (Excluding General)",
                    color='avg_sentiment',
                    color_continuous_scale='RdYlGn',
                    hover_data=['positive_count', 'negative_count']
                )
                fig.update_layout(xaxis_title="Brand Category", yaxis_title="Post Count")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.scatter(
                    brand_df,
                    x='post_count',
                    y='avg_sentiment',
                    size='avg_engagement',
                    color='brand_category',
                    title="Brand Performance Matrix",
                    color_discrete_map=brand_colors,
                    hover_data=['positive_count', 'negative_count']
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No brand category data available for selected filters (excluding general category).")
        
        # Timeline Analysis
        st.subheader("📈 Sentiment Timeline")
        
        timeline_query = f'''
        SELECT 
            DATE(timestamp) as date,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as post_count,
            SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count
        FROM social_posts 
        WHERE {filter_clause} 
        AND timestamp IS NOT NULL 
        AND timestamp != ''
        AND timestamp != 'null'
        GROUP BY DATE(timestamp)
        ORDER BY date DESC
        LIMIT 30
        '''
        
        timeline_df = pd.read_sql_query(timeline_query, conn)
        
        if not timeline_df.empty:
            timeline_df = timeline_df.sort_values('date')  # Sort chronologically for display
            
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Daily Average Sentiment (Valid Dates Only)', 'Daily Post Volume (Valid Dates Only)'),
                vertical_spacing=0.1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=timeline_df['date'], 
                    y=timeline_df['avg_sentiment'],
                    mode='lines+markers',
                    name='Avg Sentiment',
                    line=dict(color='#2E8B57', width=3),
                    hovertemplate='Date: %{x}<br>Sentiment: %{y:.3f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
            
            fig.add_trace(
                go.Bar(
                    x=timeline_df['date'],
                    y=timeline_df['post_count'],
                    name='Post Count',
                    marker_color='#1f77b4',
                    hovertemplate='Date: %{x}<br>Posts: %{y}<extra></extra>'
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                height=600,
                title_text="Daily Sentiment & Volume Trends (Excluding NULL Timestamps)",
                showlegend=True
            )
            
            fig.update_xaxes(title_text="Date", row=2, col=1)
            fig.update_yaxes(title_text="Sentiment Score", row=1, col=1)
            fig.update_yaxes(title_text="Post Count", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Add info about data quality
            conn_temp = sqlite3.connect(db.db_path)
            data_quality_query = '''
            SELECT 
                COUNT(*) as total_posts,
                SUM(CASE WHEN timestamp IS NOT NULL AND timestamp != '' AND timestamp != 'null' THEN 1 ELSE 0 END) as posts_with_valid_dates,
                SUM(CASE WHEN timestamp IS NULL OR timestamp = '' OR timestamp = 'null' THEN 1 ELSE 0 END) as posts_with_null_dates
            FROM social_posts
            '''
            quality_result = pd.read_sql_query(data_quality_query, conn_temp)
            conn_temp.close()
            
            if not quality_result.empty:
                total = quality_result.iloc[0]['total_posts']
                valid = quality_result.iloc[0]['posts_with_valid_dates']
                null_dates = quality_result.iloc[0]['posts_with_null_dates']
                
                st.info(f"📊 Data Quality: {valid:,} posts with valid dates, {null_dates:,} posts with missing timestamps out of {total:,} total posts")
        else:
            st.warning("⚠️ No posts with valid timestamps found for the selected filters.")
            st.info("💡 Most posts in the database appear to have NULL timestamps. This is likely due to data collection issues where timestamp data wasn't properly captured.")
        
        # Keyword Analysis
        st.subheader("🔥 Keyword Analysis")
        try:
            keyword_query = f'''
            SELECT 
                keyword_matched,
                COUNT(*) as mention_count,
                AVG(sentiment_score) as avg_sentiment,
                SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count
            FROM social_posts 
            WHERE keyword_matched IS NOT NULL AND keyword_matched != ''
            AND keyword_matched NOT LIKE '%rum%'
            AND {filter_clause}
            GROUP BY keyword_matched
            ORDER BY mention_count DESC
            LIMIT 10
            '''
            
            keyword_df = pd.read_sql_query(keyword_query, conn)
            
            if not keyword_df.empty:
                col1, col2 = st.columns(2)
                
                with col1:
                    fig = px.bar(keyword_df, 
                                x='mention_count', 
                                y='keyword_matched',
                                orientation='h',
                                title="Most Mentioned Keywords (Excluding Rum Terms)",
                                color='avg_sentiment',
                                color_continuous_scale='RdYlGn',
                                hover_data=['positive_count', 'negative_count'])
                    fig.update_layout(yaxis_title="Keywords", xaxis_title="Mentions")
                    st.plotly_chart(fig, use_container_width=True)
                
                with col2:
                    fig = px.pie(keyword_df, 
                                values='mention_count', 
                                names='keyword_matched',
                                title="Keyword Mention Distribution")
                    fig.update_traces(textposition='inside', textinfo='percent+label')
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No keyword data available for selected filters (excluding rum terms).")
                
        except Exception as e:
            st.error(f"Error loading keyword analysis: {e}")
        
        # Top Performing Content
        st.subheader("🔥 Top Performing Content")
        
        top_posts_query = f'''
        SELECT 
            platform,
            text,
            author,
            sentiment_label,
            sentiment_score,
            ({engagement_formula}) as total_engagement,
            timestamp,
            brand_category,
            keyword_matched
        FROM social_posts 
        WHERE {filter_clause}
        ORDER BY total_engagement DESC
        LIMIT 15
        '''
        
        top_posts_df = pd.read_sql_query(top_posts_query, conn)
        
        if not top_posts_df.empty:
            with st.expander("View Top 15 Most Engaging Posts"):
                for _, post in top_posts_df.iterrows():
                    sentiment_class = f"{post['sentiment_label']}-sentiment" if post['sentiment_label'] else "neutral-sentiment"
                    engagement = int(post['total_engagement']) if post['total_engagement'] else 0
                    brand = post['brand_category'] if post['brand_category'] else 'unknown'
                    keyword = post['keyword_matched'] if post['keyword_matched'] else 'none'
                    sentiment_score = f"{post['sentiment_score']:.3f}" if post['sentiment_score'] is not None else "0.000"
                    post_text = str(post['text']) if post['text'] else ""
                    text_preview = post_text[:200] + ('...' if len(post_text) > 200 else '')
                    
                    st.markdown(f"""
                    <div class="{sentiment_class}">
                        <strong>{post['platform'].title()}</strong> | 
                        <strong>@{post['author']}</strong> | 
                        Brand: {brand} | Keyword: {keyword} |
                        Engagement: {engagement} | 
                        Sentiment: {sentiment_score}
                        <br>
                        <em>"{text_preview}"</em>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Recent Posts Section
        st.subheader("📰 Recent Posts Sample")
        try:
            recent_query = f'''
            SELECT 
                platform,
                author,
                CASE 
                    WHEN LENGTH(text) > 150 THEN SUBSTR(text, 1, 150) || '...'
                    ELSE text
                END as text_preview,
                sentiment_label,
                ROUND(sentiment_score, 3) as sentiment_score,
                CASE 
                    WHEN timestamp IS NOT NULL AND timestamp != '' AND timestamp != 'null' 
                    THEN DATETIME(timestamp)
                    ELSE 'No date available'
                END as timestamp,
                brand_category,
                keyword_matched,
                ({engagement_formula}) as engagement
            FROM social_posts 
            WHERE {filter_clause}
            ORDER BY 
                CASE 
                    WHEN timestamp IS NOT NULL AND timestamp != '' AND timestamp != 'null' 
                    THEN timestamp 
                    ELSE '1900-01-01' 
                END DESC,
                id DESC
            LIMIT 20
            '''
            
            recent_df = pd.read_sql_query(recent_query, conn)
            
            if not recent_df.empty:
                def highlight_sentiment(row):
                    if row['sentiment_label'] == 'positive':
                        return ['background-color: #d4edda'] * len(row)
                    elif row['sentiment_label'] == 'negative':
                        return ['background-color: #f8d7da'] * len(row)
                    else:
                        return ['background-color: #e2e3e5'] * len(row)
                
                styled_df = recent_df.style.apply(highlight_sentiment, axis=1)
                st.dataframe(styled_df, use_container_width=True, hide_index=True)
                
                # Show data quality info
                null_timestamp_count = len(recent_df[recent_df['timestamp'] == 'No date available'])
                if null_timestamp_count > 0:
                    st.warning(f"⚠️ {null_timestamp_count} out of {len(recent_df)} recent posts have missing timestamps")
            else:
                st.info("No recent posts available.")
                
        except Exception as e:
            st.error(f"Error loading recent posts: {e}")
        
        # Export functionality
        st.subheader("📥 Export Data")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📊 Export Summary Stats"):
                summary_data = {
                    'Metric': ['Total Posts', 'Average Sentiment', 'Positive %', 'Negative %', 'Neutral %', 'Platforms'],
                    'Value': [
                        int(stats['total_posts']),
                        f"{float(stats['avg_sentiment']) if stats['avg_sentiment'] else 0:.3f}",
                        f"{(stats['positive_count'] / stats['total_posts'] * 100) if stats['total_posts'] > 0 else 0:.1f}%",
                        f"{(stats['negative_count'] / stats['total_posts'] * 100) if stats['total_posts'] > 0 else 0:.1f}%",
                        f"{(stats['neutral_count'] / stats['total_posts'] * 100) if stats['total_posts'] > 0 else 0:.1f}%",
                        int(stats['platforms_covered']) if stats['platforms_covered'] else 0
                    ]
                }
                summary_df = pd.DataFrame(summary_data)
                csv = summary_df.to_csv(index=False)
                st.download_button(
                    label="Download Summary CSV",
                    data=csv,
                    file_name=f"bacardi_summary_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv"
                )
        
        with col2:
            if st.button("📈 Export Timeline Data"):
                if not timeline_df.empty:
                    csv = timeline_df.to_csv(index=False)
                    st.download_button(
                        label="Download Timeline CSV",
                        data=csv,
                        file_name=f"bacardi_timeline_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
        
        with col3:
            if st.button("🔥 Export Top Posts"):
                if not top_posts_df.empty:
                    csv = top_posts_df.to_csv(index=False)
                    st.download_button(
                        label="Download Top Posts CSV",
                        data=csv,
                        file_name=f"bacardi_top_posts_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
        
        conn.close()
    
    except Exception as e:
        st.error(f"Error loading dashboard data: {e}")
        st.error("Please check your database connection and ensure data has been collected.")
    
    # Footer with database info
    try:
        conn = sqlite3.connect(db.db_path)
        
        footer_query = '''
        SELECT 
            COUNT(*) as total_posts,
            COUNT(DISTINCT platform) as platforms,
            MIN(timestamp) as earliest,
            MAX(timestamp) as latest,
            SUM(CASE WHEN sentiment_label IS NOT NULL THEN 1 ELSE 0 END) as processed_posts
        FROM social_posts
        '''
        
        footer_df = pd.read_sql_query(footer_query, conn)
        conn.close()
        
        if not footer_df.empty:
            info = footer_df.iloc[0]
            
            footer_text = (
                f"📊 Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Total Posts: {int(info['total_posts']):,} | "
                f"Processed: {int(info['processed_posts']):,} | "
                f"Platforms: {int(info['platforms'])}"
            )
            
            if info['earliest'] and info['latest']:
                footer_text += f" | Period: {info['earliest'][:10]} to {info['latest'][:10]}"
            
            if info['processed_posts'] < info['total_posts']:
                footer_text += f" | ⚠️ {int(info['total_posts']) - int(info['processed_posts'])} posts need sentiment analysis"
            
            st.caption(footer_text)
        
    except Exception as e:
        st.caption(f"📊 Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
