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
    
    if engagement_calc:
        return ' + '.join(engagement_calc)
    else:
        return '0'

def main():
    st.markdown('<h1 class="main-header">🥃 Bacardi Historical Sentiment Analysis (2019-2024)</h1>', unsafe_allow_html=True)
    st.markdown("**5-Year Multi-Platform Analysis:** Reddit • YouTube • Facebook • Instagram")
    
    # Initialize database
    db = init_database()
    if not db:
        st.stop()
    
    # Sidebar controls
    st.sidebar.header("📊 Historical Dashboard Controls")
    
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
                st.sidebar.info("Run: python analyze_sentiment_final.py")
            else:
                st.sidebar.success("✅ All posts analyzed!")
        
    except Exception as e:
        st.sidebar.error(f"Error checking analysis status: {e}")
    
    # Time period filter - Extended for 5 years
    st.sidebar.subheader("📅 Time Period")
    date_range = st.sidebar.selectbox(
        "Select time period:",
        ["All 5 years (2019-2024)", "Last 2 years", "Last 1 year", "Last 6 months", "Last 3 months", "Last 30 days"],
        index=0
    )
    
    # Year filter
    st.sidebar.subheader("📆 Year Filter")
    available_years = ["All Years", "2024", "2023", "2022", "2021", "2020", "2019"]
    selected_year = st.sidebar.selectbox("Select specific year:", available_years)
    
    # Platform filter
    st.sidebar.subheader("🔧 Platform Filter")
    available_platforms = ["All", "reddit", "youtube", "facebook", "instagram"]
    selected_platform = st.sidebar.selectbox("Select platform:", available_platforms)
    
    # Sentiment filter
    st.sidebar.subheader("😊 Sentiment Filter")
    sentiment_filter = st.sidebar.selectbox("Select sentiment:", ["All", "positive", "negative", "neutral"])
    
    # Advanced filters
    st.sidebar.subheader("🔍 Advanced Filters")
    min_engagement = st.sidebar.slider("Minimum engagement (likes/upvotes):", 0, 100, 0)
    show_verified_only = st.sidebar.checkbox("Verified authors only", value=False)
    
    # Platform colors
    platform_colors = {
        'reddit': '#FF4500',
        'youtube': '#FF0000', 
        'facebook': '#1877F2',
        'instagram': '#E4405F'
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
        filters = ["sentiment_label IS NOT NULL", "sentiment_label IN ('positive', 'negative', 'neutral')"]
        
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
        
        # Year filter
        if selected_year != "All Years":
            filters.append(f"strftime('%Y', timestamp) = '{selected_year}'")
        
        # Platform filter
        if selected_platform != "All":
            filters.append(f"platform = '{selected_platform}'")
        
        # Sentiment filter
        if sentiment_filter != "All":
            filters.append(f"sentiment_label = '{sentiment_filter}'")
        
        # Engagement filter
        if min_engagement > 0:
            conn_temp = sqlite3.connect(db.db_path)
            column_check = conn_temp.execute("PRAGMA table_info(social_posts)").fetchall()
            column_names = [col[1] for col in column_check]
            conn_temp.close()
            
            engagement_conditions = []
            if 'likes' in column_names:
                engagement_conditions.append(f"likes >= {min_engagement}")
            if 'upvotes' in column_names:
                engagement_conditions.append(f"upvotes >= {min_engagement}")
            
            if engagement_conditions:
                filters.append(f"({' OR '.join(engagement_conditions)})")
        
        # Verified filter
        if show_verified_only:
            filters.append("verified = 1")
        
        return " AND ".join(filters)
    
    filter_clause = build_filters()
    
    # Main dashboard content
    try:
        conn = sqlite3.connect(db.db_path)
        engagement_formula = get_engagement_formula(conn)
        
        # Overall historical metrics
        metrics_query = f'''
        SELECT 
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as total_posts,
            SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count,
            SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral_count,
            MIN(timestamp) as earliest_post,
            MAX(timestamp) as latest_post,
            COUNT(DISTINCT strftime('%Y', timestamp)) as years_covered,
            COUNT(DISTINCT platform) as platforms_covered
        FROM social_posts 
        WHERE {filter_clause}
        '''
        
        stats_df = pd.read_sql_query(metrics_query, conn)
        stats = stats_df.iloc[0] if not stats_df.empty and stats_df.iloc[0]['total_posts'] > 0 else None
        
        if stats is None or stats['total_posts'] == 0:
            st.warning("⚠️ No data available for the selected filters.")
            st.info("Try adjusting your filters or run the data collector to gather more historical data.")
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
            avg_sentiment = float(stats['avg_sentiment'])
            sentiment_emoji = "😊" if avg_sentiment > 0.1 else "😐" if avg_sentiment > -0.1 else "😞"
            st.metric(
                "📈 Avg Sentiment", 
                f"{avg_sentiment:.3f} {sentiment_emoji}",
                help="Average sentiment score (-1 to +1)"
            )
        
        with col3:
            positive_pct = (stats['positive_count'] / stats['total_posts']) * 100
            st.metric(
                "✅ Positive %", 
                f"{positive_pct:.1f}%",
                help="Percentage of posts with positive sentiment"
            )
        
        with col4:
            st.metric(
                "📅 Years Covered", 
                f"{int(stats['years_covered'])}",
                help="Number of years with data"
            )
        
        with col5:
            st.metric(
                "🌐 Platforms", 
                f"{int(stats['platforms_covered'])}",
                help="Number of platforms with data"
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
            WHERE {filter_clause}
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
                    title="Posts by Platform",
                    color='avg_sentiment',
                    color_continuous_scale='RdYlGn',
                    hover_data=['positive_count', 'negative_count']
                )
                fig.update_layout(yaxis_title="Platform", xaxis_title="Post Count", height=400)
                st.plotly_chart(fig, use_container_width=True)
                
                if 'youtube' in platform_df['platform'].values:
                    st.info("💡 YouTube comments often show detailed opinions about taste and experience")
                if 'reddit' in platform_df['platform'].values:
                    st.info("💡 Reddit discussions tend to be more conversational and authentic")
            else:
                st.info("No platform data available for selected filters.")
        
        # Historical Timeline Analysis
        st.subheader("📈 Historical Sentiment Timeline (5 Years)")
        
        timeline_query = f'''
        SELECT 
            strftime('%Y-%m', timestamp) as month,
            strftime('%Y', timestamp) as year,
            AVG(sentiment_score) as avg_sentiment,
            COUNT(*) as post_count,
            SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
            SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count
        FROM social_posts 
        WHERE {filter_clause}
        GROUP BY strftime('%Y-%m', timestamp)
        ORDER BY month
        '''
        
        timeline_df = pd.read_sql_query(timeline_query, conn)
        
        if not timeline_df.empty:
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Monthly Average Sentiment', 'Monthly Post Volume'),
                vertical_spacing=0.1,
                specs=[[{"secondary_y": False}], [{"secondary_y": False}]]
            )
            
            fig.add_trace(
                go.Scatter(
                    x=timeline_df['month'], 
                    y=timeline_df['avg_sentiment'],
                    mode='lines+markers',
                    name='Avg Sentiment',
                    line=dict(color='#2E8B57', width=3),
                    hovertemplate='Month: %{x}<br>Sentiment: %{y:.3f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)
            
            fig.add_trace(
                go.Bar(
                    x=timeline_df['month'],
                    y=timeline_df['post_count'],
                    name='Post Count',
                    marker_color='#1f77b4',
                    hovertemplate='Month: %{x}<br>Posts: %{y}<extra></extra>'
                ),
                row=2, col=1
            )
            
            fig.update_layout(
                height=600,
                title_text="5-Year Historical Analysis",
                showlegend=True
            )
            
            fig.update_xaxes(title_text="Month", row=2, col=1)
            fig.update_yaxes(title_text="Sentiment Score", row=1, col=1)
            fig.update_yaxes(title_text="Post Count", row=2, col=1)
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Year-by-Year Analysis
        st.subheader("📊 Year-by-Year Analysis")
        
        yearly_query = f'''
        SELECT 
            strftime('%Y', timestamp) as year,
            COUNT(*) as posts,
            AVG(sentiment_score) as avg_sentiment,
            SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive,
            SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative,
            SUM(CASE WHEN sentiment_label = 'neutral' THEN 1 ELSE 0 END) as neutral,
            AVG({engagement_formula}) as avg_engagement
        FROM social_posts 
        WHERE {filter_clause}
        GROUP BY strftime('%Y', timestamp)
        ORDER BY year DESC
        '''
        
        yearly_df = pd.read_sql_query(yearly_query, conn)
        
        if not yearly_df.empty:
            years_to_show = yearly_df.head(6)
            cols = st.columns(len(years_to_show))
            
            for i, (_, row) in enumerate(years_to_show.iterrows()):
                with cols[i]:
                    year = int(row['year'])
                    posts = int(row['posts'])
                    sentiment = float(row['avg_sentiment'])
                    positive_pct = (row['positive'] / posts * 100) if posts > 0 else 0
                    
                    st.markdown(f"""
                    <div class="year-stats">
                        <h3>{year}</h3>
                        <p><strong>{posts:,}</strong> posts</p>
                        <p><strong>{sentiment:.3f}</strong> avg sentiment</p>
                        <p><strong>{positive_pct:.1f}%</strong> positive</p>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Platform Performance
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🏆 Platform Performance Comparison")
            
            platform_performance_query = f'''
            SELECT 
                platform,
                COUNT(*) as total_posts,
                AVG(sentiment_score) as avg_sentiment,
                SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                AVG({engagement_formula}) as avg_engagement,
                MIN(timestamp) as first_post,
                MAX(timestamp) as latest_post
            FROM social_posts 
            WHERE {filter_clause}
            GROUP BY platform
            ORDER BY total_posts DESC
            '''
            
            platform_perf_df = pd.read_sql_query(platform_performance_query, conn)
            
            if not platform_perf_df.empty:
                fig = px.scatter(
                    platform_perf_df,
                    x='total_posts',
                    y='avg_sentiment',
                    size='avg_engagement',
                    color='platform',
                    color_discrete_map=platform_colors,
                    title="Platform Performance Matrix",
                    labels={
                        'total_posts': 'Total Posts',
                        'avg_sentiment': 'Average Sentiment',
                        'avg_engagement': 'Avg Engagement'
                    },
                    hover_data=['positive_count']
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("📅 Platform Timeline")
            
            platform_timeline_query = f'''
            SELECT 
                platform,
                strftime('%Y', timestamp) as year,
                COUNT(*) as posts
            FROM social_posts 
            WHERE {filter_clause}
            GROUP BY platform, strftime('%Y', timestamp)
            ORDER BY year, platform
            '''
            
            platform_timeline_df = pd.read_sql_query(platform_timeline_query, conn)
            
            if not platform_timeline_df.empty:
                fig = px.line(
                    platform_timeline_df,
                    x='year',
                    y='posts',
                    color='platform',
                    color_discrete_map=platform_colors,
                    title="Platform Activity Over Years",
                    markers=True
                )
                fig.update_layout(height=400)
                st.plotly_chart(fig, use_container_width=True)
        
        # Sentiment Evolution
        st.subheader("🎭 Sentiment Evolution Analysis")
        
        sentiment_evolution_query = f'''
        SELECT 
            strftime('%Y', timestamp) as year,
            sentiment_label,
            COUNT(*) as count
        FROM social_posts 
        WHERE {filter_clause}
        GROUP BY strftime('%Y', timestamp), sentiment_label
        ORDER BY year, sentiment_label
        '''
        
        sentiment_evolution_df = pd.read_sql_query(sentiment_evolution_query, conn)
        
        if not sentiment_evolution_df.empty:
            fig = px.bar(
                sentiment_evolution_df,
                x='year',
                y='count',
                color='sentiment_label',
                color_discrete_map=sentiment_colors,
                title="Sentiment Distribution by Year",
                labels={'count': 'Number of Posts', 'year': 'Year'}
            )
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)
        
        # Keyword Analysis
        st.subheader("🔥 Keyword Analysis")
        try:
            column_check = conn.execute("PRAGMA table_info(social_posts)").fetchall()
            column_names = [col[1] for col in column_check]
            
            if 'keyword_matched' in column_names:
                keyword_query = f'''
                SELECT 
                    keyword_matched,
                    COUNT(*) as mention_count,
                    AVG(sentiment_score) as avg_sentiment,
                    SUM(CASE WHEN sentiment_label = 'positive' THEN 1 ELSE 0 END) as positive_count,
                    SUM(CASE WHEN sentiment_label = 'negative' THEN 1 ELSE 0 END) as negative_count
                FROM social_posts 
                WHERE keyword_matched IS NOT NULL AND keyword_matched != ''
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
                                    title="Most Mentioned Keywords",
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
                        
                    keyword_trends_query = f'''
                    SELECT 
                        keyword_matched,
                        strftime('%Y', timestamp) as year,
                        COUNT(*) as mentions,
                        AVG(sentiment_score) as avg_sentiment
                    FROM social_posts 
                    WHERE keyword_matched IS NOT NULL 
                    AND keyword_matched != ''
                    AND {filter_clause}
                    GROUP BY keyword_matched, strftime('%Y', timestamp)
                    ORDER BY year, mentions DESC
                    '''
                    
                    keyword_trends_df = pd.read_sql_query(keyword_trends_query, conn)
                    
                    if not keyword_trends_df.empty:
                        top_keywords = keyword_df.head(5)['keyword_matched'].values
                        filtered_trends = keyword_trends_df[keyword_trends_df['keyword_matched'].isin(top_keywords)]
                        
                        if not filtered_trends.empty:
                            fig = px.line(
                                filtered_trends,
                                x='year',
                                y='mentions',
                                color='keyword_matched',
                                title="Top 5 Keywords Trend Over Years",
                                markers=True
                            )
                            fig.update_layout(height=400)
                            st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No keyword data available.")
            else:
                text_analysis_query = f'''
                SELECT 
                    CASE 
                        WHEN LOWER(text) LIKE '%bacardi%' THEN 'bacardi'
                        WHEN LOWER(text) LIKE '%breezer%' THEN 'breezer'
                        WHEN LOWER(text) LIKE '%rum%' THEN 'rum'
                        WHEN LOWER(text) LIKE '%superior%' THEN 'superior'
                        WHEN LOWER(text) LIKE '%gold%' THEN 'gold'
                        ELSE 'other'
                    END as keyword,
                    COUNT(*) as mention_count,
                    AVG(sentiment_score) as avg_sentiment
                FROM social_posts 
                WHERE {filter_clause}
                GROUP BY keyword
                ORDER BY mention_count DESC
                '''
                
                keyword_df = pd.read_sql_query(text_analysis_query, conn)
                
                if not keyword_df.empty:
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        fig = px.bar(keyword_df, 
                                    x='mention_count', 
                                    y='keyword',
                                    orientation='h',
                                    title="Keywords Found in Text",
                                    color='avg_sentiment',
                                    color_continuous_scale='RdYlGn')
                        fig.update_layout(yaxis_title="Keywords", xaxis_title="Mentions")
                        st.plotly_chart(fig, use_container_width=True)
                    
                    with col2:
                        fig = px.pie(keyword_df, 
                                    values='mention_count', 
                                    names='keyword',
                                    title="Text-based Keyword Distribution")
                        fig.update_traces(textposition='inside', textinfo='percent+label')
                        st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No keyword analysis available.")
                    
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
            strftime('%Y', timestamp) as year
        FROM social_posts 
        WHERE {filter_clause}
        ORDER BY total_engagement DESC
        LIMIT 20
        '''
        
        top_posts_df = pd.read_sql_query(top_posts_query, conn)
        
        if not top_posts_df.empty:
            with st.expander("View Top 20 Most Engaging Posts"):
                for _, post in top_posts_df.iterrows():
                    sentiment_class = f"{post['sentiment_label']}-sentiment"
                    st.markdown(f"""
                    <div class="{sentiment_class}">
                        <strong>{post['platform'].title()}</strong> | <strong>{post['year']}</strong> | 
                        <strong>@{post['author']}</strong> | 
                        Engagement: {int(post['total_engagement'])} | 
                        Sentiment: {post['sentiment_score']:.3f}
                        <br>
                        <em>"{post['text'][:200]}{'...' if len(post['text']) > 200 else ''}"</em>
                    </div>
                    """, unsafe_allow_html=True)
        
        # Top Contributors
        st.subheader("👥 Top Contributors")
        try:
            authors_query = f'''
            SELECT 
                author,
                platform,
                COUNT(*) as post_count,
                AVG(sentiment_score) as avg_sentiment,
                MAX(COALESCE(followers, 0)) as followers,
                SUM({engagement_formula}) as total_engagement
            FROM social_posts 
            WHERE author IS NOT NULL AND author != 'deleted' AND author != 'unknown'
            AND {filter_clause}
            GROUP BY author, platform
            HAVING post_count > 1
            ORDER BY post_count DESC, total_engagement DESC
            LIMIT 15
            '''
            
            authors_df = pd.read_sql_query(authors_query, conn)
            
            if not authors_df.empty:
                fig = px.scatter(
                    authors_df, 
                    x='post_count', 
                    y='avg_sentiment',
                    size='total_engagement',
                    color='platform',
                    hover_data=['author', 'followers'],
                    title="Top Authors by Post Count vs Sentiment",
                    color_discrete_map=platform_colors
                )
                fig.update_layout(
                    xaxis_title="Post Count", 
                    yaxis_title="Average Sentiment",
                    height=500
                )
                fig.add_hline(y=0, line_dash="dash", line_color="gray")
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No author data available for selected filters.")
                
        except Exception as e:
            st.error(f"Error loading author analysis: {e}")
        
        # Recent Posts Section
        st.subheader("📰 Recent Posts Sample")
        try:
            column_check = conn.execute("PRAGMA table_info(social_posts)").fetchall()
            column_names = [col[1] for col in column_check]
            
            base_query = f'''
            SELECT 
                platform,
                author,
                CASE 
                    WHEN LENGTH(text) > 150 THEN SUBSTR(text, 1, 150) || '...'
                    ELSE text
                END as text_preview,
                sentiment_label,
                ROUND(sentiment_score, 3) as sentiment_score,
                DATETIME(timestamp) as timestamp'''
            
            if 'likes' in column_names and 'comments' in column_names:
                if 'upvotes' in column_names:
                    engagement_query = ''',
                    CASE
                        WHEN platform = 'reddit' THEN COALESCE(upvotes, 0) || ' upvotes, ' || COALESCE(comments, 0) || ' comments'
                        WHEN platform = 'youtube' THEN COALESCE(likes, 0) || ' likes'
                        WHEN platform = 'facebook' THEN COALESCE(likes, 0) || ' likes, ' || COALESCE(comments, 0) || ' comments'
                        WHEN platform = 'instagram' THEN COALESCE(likes, 0) || ' likes, ' || COALESCE(comments, 0) || ' comments'
                        ELSE 'N/A'
                    END as engagement'''
                else:
                    engagement_query = ''',
                    CASE
                        WHEN platform = 'youtube' THEN COALESCE(likes, 0) || ' likes'
                        WHEN platform = 'facebook' THEN COALESCE(likes, 0) || ' likes, ' || COALESCE(comments, 0) || ' comments'
                        WHEN platform = 'instagram' THEN COALESCE(likes, 0) || ' likes, ' || COALESCE(comments, 0) || ' comments'
                        ELSE COALESCE(likes, 0) || ' likes, ' || COALESCE(comments, 0) || ' comments'
                    END as engagement'''
            else:
                engagement_query = ""
            
            recent_query = base_query + engagement_query + f'''
            FROM social_posts 
            WHERE {filter_clause}
            ORDER BY timestamp DESC 
            LIMIT 25
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
            else:
                st.info("No recent posts available.")
                
        except Exception as e:
            st.error(f"Error loading recent posts: {e}")
        
        # Export functionality
        st.subheader("📥 Export Historical Data")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 Export Summary Stats"):
                summary_data = {
                    'Metric': ['Total Posts', 'Average Sentiment', 'Positive %', 'Negative %', 'Neutral %', 'Years Covered'],
                    'Value': [
                        int(stats['total_posts']),
                        f"{float(stats['avg_sentiment']):.3f}",
                        f"{(stats['positive_count'] / stats['total_posts'] * 100):.1f}%",
                        f"{(stats['negative_count'] / stats['total_posts'] * 100):.1f}%",
                        f"{(stats['neutral_count'] / stats['total_posts'] * 100):.1f}%",
                        int(stats['years_covered'])
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
            if st.button("🏆 Export Top Posts"):
                if not top_posts_df.empty:
                    csv = top_posts_df.to_csv(index=False)
                    st.download_button(
                        label="Download Top Posts CSV",
                        data=csv,
                        file_name=f"bacardi_top_posts_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
        
        with col4:
            if st.button("🔥 Export Keyword Data"):
                if 'keyword_df' in locals() and not keyword_df.empty:
                    csv = keyword_df.to_csv(index=False)
                    st.download_button(
                        label="Download Keywords CSV",
                        data=csv,
                        file_name=f"bacardi_keywords_{datetime.now().strftime('%Y%m%d')}.csv",
                        mime="text/csv"
                    )
        
        conn.close()
    
    except Exception as e:
        st.error(f"Error loading historical dashboard data: {e}")
        st.error("Please check your database connection and ensure data has been collected.")
    
    # Footer with comprehensive database info
    try:
        conn = sqlite3.connect(db.db_path)
        
        footer_query = '''
        SELECT 
            COUNT(*) as total_posts,
            COUNT(DISTINCT platform) as platforms,
            COUNT(DISTINCT strftime('%Y', timestamp)) as years,
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
                f"📊 Historical Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
                f"Total Posts: {int(info['total_posts']):,} | "
                f"Processed: {int(info['processed_posts']):,} | "
                f"Platforms: {int(info['platforms'])} | "
                f"Years: {int(info['years'])} | "
                f"Period: {info['earliest'][:10]} to {info['latest'][:10]}"
            )
            
            if info['processed_posts'] < info['total_posts']:
                footer_text += f" | ⚠️ {int(info['total_posts']) - int(info['processed_posts'])} posts need sentiment analysis"
            
            st.caption(footer_text)
        
    except Exception as e:
        st.caption(f"📊 Historical Dashboard | Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()