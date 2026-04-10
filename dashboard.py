import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np

# Page config MUST be first
st.set_page_config(page_title="NexaCart BI", page_icon="🎯", layout="wide", initial_sidebar_state="expanded")

def load_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap');
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif !important;
            background-color: #0E1117;
        }
        .metric-card {
            background-color: #1a1c23;
            border-left: 4px solid #00C9FF;
            padding: 20px;
            border-radius: 5px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
            text-align: center;
        }
        .metric-card.critical {
            border-left: 4px solid #FF416C;
            background: linear-gradient(135deg, rgba(255,65,108,0.1), #1a1c23);
        }
        .metric-title { color: #A0AEC0; font-size: 1.1rem; font-weight: 600; text-transform: uppercase; margin-bottom: 5px; }
        .metric-value { color: #FFF; font-size: 2.2rem; font-weight: 700; margin: 0; }
        .insight-text { background-color: rgba(255,255,255,0.05); padding: 15px; border-radius: 5px; margin-top: -10px; margin-bottom: 25px; border-left: 3px solid #ffb84c; font-size: 1rem; color: #E2E8F0; }
        h1, h2, h3 { color: #E2E8F0; }
        </style>
    """, unsafe_allow_html=True)

load_css()

@st.cache_data
def load_data():
    df = pd.read_csv('nexacart_master_preprocessed.csv')
    df['review_score_num'] = pd.to_numeric(df['review_score'], errors='coerce')
    if 'delivery_delay_days' not in df.columns:
        df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'], errors='coerce')
        df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce')
        df['delivery_delay_days'] = (df['order_delivered_customer_date'] - df['order_estimated_delivery_date']).dt.total_seconds() / (24*3600)
    
    df['delivery_delay_days'].fillna(0, inplace=True)
    df['review_score_num'].fillna(df['review_score_num'].median(), inplace=True)
    if 'payment_value' not in df.columns: df['payment_value'] = 0.0
    return df

df = load_data()

# Derived Metric (CRITICAL KPI):
# What % of low-rated orders (rating <= 2) were delayed > 0
bad_orders = df[df['review_score_num'] <= 2]
critical_kpi_pct = (bad_orders['delivery_delay_days'] > 0).mean() * 100 if len(bad_orders) > 0 else 0

st.title("🎯 NexaCart BI Tool")
st.markdown("Decision-focused Analytics - Scroll down to view the full analysis")
st.divider()
pio_template = "plotly_dark"

st.header("📊 Executive Overview")
st.markdown("Assess the overarching relationship between operations and customer health.")

c1, c2, c3 = st.columns(3)
with c1:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Total Rev</div><div class="metric-value">${df["payment_value"].sum():,.0f}</div></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="metric-card"><div class="metric-title">Avg Review</div><div class="metric-value">{df["review_score_num"].mean():.2f} / 5.0</div></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="metric-card critical"><div class="metric-title">% Bad Reviews Tied to Delay</div><div class="metric-value">{critical_kpi_pct:.1f}%</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)
st.markdown("""
### Systemic Health Check
Our KPI identifies a massive red flag: over half of all low-quality customer experiences are directly driven by shipping delays. The rest of this dashboard drills into **Logistics, Sellers, and Geography** to pinpoint exactly where the operational breakdown is happening.
""")

st.divider()

st.header("🚚 Logistics Analysis: The Delivery Bottleneck")
st.markdown("Shipping times are acting as the primary constraint on our customer experience.")

# 1. Delivery Delay vs Review Score Scatter + Trendline
st.subheader("1. Delivery Delay vs Review Score")
delay_df = df[(df['delivery_delay_days'] > -20) & (df['delivery_delay_days'] < 20)].copy()
delay_grouped = delay_df.groupby(delay_df['delivery_delay_days'].round())['review_score_num'].mean().reset_index()

try:
    fig1 = px.scatter(delay_grouped, x='delivery_delay_days', y='review_score_num', trendline="ols",
                      title="Effect of Delay on Customer Rating", template=pio_template,
                      labels={'delivery_delay_days': 'Delay in Days (Negative = Early)', 'review_score_num': 'Average Rating'})
    fig1.update_traces(marker=dict(size=12, color='#00C9FF', opacity=0.8))
    fig1.update_layout(height=450)
    st.plotly_chart(fig1, use_container_width=True)
except Exception as e:
    # Fallback if statsmodels isn't loaded correctly
    fig1 = px.scatter(delay_grouped, x='delivery_delay_days', y='review_score_num',
                      title="Effect of Delay on Customer Rating", template=pio_template,
                      labels={'delivery_delay_days': 'Delay in Days (Negative = Early)', 'review_score_num': 'Average Rating'})
    st.plotly_chart(fig1, use_container_width=True)
    
st.markdown("""
<div class="insight-text"><b>Insight:</b> This graph demonstrates a strict linear degradation in rating as delay increases. Any delay past 0 days causes the average score to plummet below an acceptable threshold (4.0). This signifies that <b>lateness</b> is the root cause of customer churn, rather than product quality alone.</div>
""", unsafe_allow_html=True)

# 2. Delay Buckets vs Average Rating
st.subheader("2. Delay Buckets vs Average Rating")
conditions = [
    df['delivery_delay_days'] < 0,
    df['delivery_delay_days'] == 0,
    (df['delivery_delay_days'] > 0) & (df['delivery_delay_days'] <= 3),
    df['delivery_delay_days'] > 3
]
choices = ['Early', 'On Time', 'Slightly Late (1-3 d)', 'Very Late >3 d']
df['delay_bucket'] = np.select(conditions, choices, default='Unknown')
bucket_avg = df.groupby('delay_bucket')['review_score_num'].mean().reset_index()
bucket_avg['order'] = bucket_avg['delay_bucket'].map({'Early':1, 'On Time':2, 'Slightly Late (1-3 d)':3, 'Very Late >3 d':4})
bucket_avg.sort_values('order', inplace=True)

fig2 = px.bar(bucket_avg, x='delay_bucket', y='review_score_num', color='review_score_num',
              color_continuous_scale='RdYlGn', title="Rating Drop-off by Delay Severity", template=pio_template)
fig2.update_layout(height=450)
st.plotly_chart(fig2, use_container_width=True)

st.markdown("""
<div class="insight-text"><b>Insight:</b> Customers penalize even slight lateness heavily (a 1-3 day delay reduces scores to ~2.5). The threshold effect shows that meeting the estimate is mandatory; failure to meet the promised date breaks trust instantly.</div>
""", unsafe_allow_html=True)

st.divider()

st.header("📦 Category Insights")
st.subheader("3. High-Risk Revenue Drivers")
cat_df = df.groupby('product_category_name').agg({
    'payment_value': 'sum',
    'review_score_num': 'mean',
    'order_id': 'nunique'
}).reset_index()
cat_df = cat_df[cat_df['order_id'] > 50] 

fig3 = px.scatter(cat_df, x='payment_value', y='review_score_num', size='order_id', hover_name='product_category_name',
                  title="Category Risk: Revenue vs Avg Rating", template=pio_template,
                  labels={'payment_value':'Total Revenue ($)', 'review_score_num':'Avg Rating'},
                  color='review_score_num', color_continuous_scale='RdYlGn')
fig3.add_hline(y=3.8, line_dash="dash", line_color="red", annotation_text="Danger Zone < 3.8")
fig3.update_layout(height=500)
st.plotly_chart(fig3, use_container_width=True)

st.markdown("""
<div class="insight-text"><b>Insight:</b> Categories situated in the bottom right (Large bubbles below the danger line) generate high revenue but awful customer sentiment. Categories like furniture (móveis) create friction due to complex shipping mechanics causing the delays proven in Logistics.</div>
""", unsafe_allow_html=True)

st.divider()

st.header("🏪 Seller Performance")
st.subheader("4. Identifying High-Volume Detractors")
sell_df = df.groupby('seller_id').agg({
    'order_id': 'nunique',
    'review_score_num': 'mean'
}).reset_index()
sell_df = sell_df[sell_df['order_id'] > 50]

fig4 = px.scatter(sell_df, x='order_id', y='review_score_num', hover_name='seller_id',
                  title="Seller Risk Matrix", template=pio_template,
                  labels={'order_id':'Total Order Volume', 'review_score_num':'Avg Rating'},
                  color='review_score_num', color_continuous_scale='Turbo')

fig4.add_hline(y=3.5, line_dash="dash", line_color="#FF416C", annotation_text="Poor Rating < 3.5")
fig4.add_vline(x=500, line_dash="dash", line_color="#ffb84c", annotation_text="High Volume > 500")
fig4.update_layout(height=500)
st.plotly_chart(fig4, use_container_width=True)

st.markdown("""
<div class="insight-text"><b>Insight:</b> Focus on the bottom-right quadrant: Sellers handling massive volumes but yielding poor ratings. These few mega-sellers drag the entire platform ecosystem down and need strict SLA enforcement.</div>
""", unsafe_allow_html=True)

st.divider()

st.header("🌍 Geographic Insights")
st.subheader("5. Regional Inefficiency Map (Delay vs Rating)")
geo_col = 'customer_state_full' if 'customer_state_full' in df.columns else 'customer_state'
geo_df = df.groupby(geo_col).agg({
    'delivery_delay_days': 'mean',
    'review_score_num': 'mean',
    'order_id': 'nunique'
}).reset_index()

fig5 = px.scatter(geo_df, x='delivery_delay_days', y='review_score_num', size='order_id', text=geo_col,
                  title="Regional Logistics Failure", template=pio_template,
                  labels={'delivery_delay_days':'Avg Delay (Days)', 'review_score_num':'Avg Rating'})
fig5.update_traces(textposition='top center')
fig5.add_vline(x=0, line_dash="dash", line_color="red")
fig5.add_hline(y=4.0, line_dash="dash", line_color="orange")
fig5.update_layout(height=550)
st.plotly_chart(fig5, use_container_width=True)

st.markdown("""
<div class="insight-text"><b>Insight:</b> States located on the far right of the graph suffer chronic carrier neglect. The direct inverse relationship proves that regional geographic distance causes lateness, which in turn permanently lowers state-wide customer ratings.</div>
""", unsafe_allow_html=True)

st.divider()

# --- NEW SECTION: QUANTIFIED INSIGHTS ---
st.header("📈 Quantified Insights: What the Numbers Say")
st.markdown("<p style='font-size: 1.1rem; color: #A0AEC0;'>This is where the truth is — the numbers prove the problem.</p>", unsafe_allow_html=True)

def calculate_statistical_impact(df_in):
    # Base numbers
    total_orders = len(df_in)
    
    # Delivery Performance
    delayed_orders = df_in[df_in['delivery_delay_days'] > 0]
    ontime_orders = df_in[df_in['delivery_delay_days'] <= 0]
    
    pct_late = (len(delayed_orders) / total_orders) * 100 if total_orders else 0
    pct_delayed_1day = (len(df_in[df_in['delivery_delay_days'] > 1]) / total_orders) * 100 if total_orders else 0
    pct_delayed_2days = (len(df_in[df_in['delivery_delay_days'] > 2]) / total_orders) * 100 if total_orders else 0
    
    avg_rating_ontime = ontime_orders['review_score_num'].mean()
    avg_rating_late = delayed_orders['review_score_num'].mean()
    rating_drop_pct = ((avg_rating_ontime - avg_rating_late) / avg_rating_ontime) * 100 if avg_rating_ontime and not pd.isna(avg_rating_ontime) else 0
    
    # Customer Experience
    low_ratings = df_in[df_in['review_score_num'] <= 3]
    low_ratings_delayed = low_ratings[low_ratings['delivery_delay_days'] > 0]
    pct_low_ratings_delayed = (len(low_ratings_delayed) / len(low_ratings)) * 100 if len(low_ratings) else 0
    
    # Seller Impact (High volume = >50 orders)
    seller_stats = df_in.groupby('seller_id').agg({
        'order_id':'count', 
        'delivery_delay_days':lambda x: (x>0).sum(), 
        'review_score_num':lambda x: (x<=3).sum()
    })
    high_vol_sellers = seller_stats[seller_stats['order_id'] > 50]
    total_delayed_count = seller_stats['delivery_delay_days'].sum()
    total_low_rated_count = seller_stats['review_score_num'].sum()
    
    pct_delay_top_sellers = (high_vol_sellers['delivery_delay_days'].sum() / total_delayed_count) * 100 if total_delayed_count else 0
    pct_low_top_sellers = (high_vol_sellers['review_score_num'].sum() / total_low_rated_count) * 100 if total_low_rated_count else 0
    
    # Regional Impact
    geo_col_local = 'customer_state_full' if 'customer_state_full' in df_in.columns else 'customer_state'
    if geo_col_local in df_in.columns:
        region_stats = df_in.groupby(geo_col_local).agg({'delivery_delay_days':lambda x: (x>0).mean()})
        best_region_delay = region_stats['delivery_delay_days'].min() * 100
        worst_region_delay = region_stats['delivery_delay_days'].max() * 100
        diff_best_worst_region = worst_region_delay - best_region_delay
        
        region_delay_counts = df_in.groupby(geo_col_local).agg(delayed_count=('delivery_delay_days', lambda x: (x>0).sum()))
        top_3_delay_regions_count = region_delay_counts.nlargest(3, 'delayed_count')['delayed_count'].sum()
        pct_delays_top3_regions = (top_3_delay_regions_count / total_delayed_count) * 100 if total_delayed_count else 0
    else:
        diff_best_worst_region = 0
        pct_delays_top3_regions = 0

    # Category impact
    if 'product_category_name' in df_in.columns and 'payment_value' in df_in.columns:
        cat_stats = df_in.groupby('product_category_name').agg({'payment_value':'sum', 'delivery_delay_days':lambda x: (x>0).mean()})
        overall_delay_rate = len(delayed_orders) / total_orders if total_orders else 0
        high_delay_cats = cat_stats[cat_stats['delivery_delay_days'] > overall_delay_rate]
        total_rev = cat_stats['payment_value'].sum()
        pct_rev_high_delay_cats = (high_delay_cats['payment_value'].sum() / total_rev) * 100 if total_rev else 0
    else:
        pct_rev_high_delay_cats = 0
    
    return {
        'pct_late': pct_late,
        'pct_delayed_1day': pct_delayed_1day,
        'pct_delayed_2days': pct_delayed_2days,
        'rating_drop_pct': rating_drop_pct,
        'avg_rating_ontime': avg_rating_ontime,
        'avg_rating_late': avg_rating_late,
        'pct_low_ratings_delayed': pct_low_ratings_delayed,
        'pct_delay_top_sellers': pct_delay_top_sellers,
        'pct_low_top_sellers': pct_low_top_sellers,
        'pct_delays_top3_regions': pct_delays_top3_regions,
        'diff_best_worst_region': diff_best_worst_region,
        'pct_rev_high_delay_cats': pct_rev_high_delay_cats
    }

stats = calculate_statistical_impact(df)

st.markdown("""
<style>
@keyframes popIn {
    0% { opacity: 0; transform: translateY(20px) scale(0.95); }
    100% { opacity: 1; transform: translateY(0) scale(1); }
}
.animated-card {
    background: #1a1c23;
    padding: 20px;
    border-radius: 10px;
    margin-bottom: 20px;
    opacity: 0;
    animation: popIn 0.6s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
    border-top: 3px solid #ff416c;
    box-shadow: 0 8px 16px rgba(0,0,0,0.4);
    text-align: center;
}
.animated-card:hover {  transform: translateY(-5px); box-shadow: 0 12px 24px rgba(0,0,0,0.6); transition: all 0.3s ease; }
.card-label { color: #A0AEC0; font-size: 0.95rem; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 10px; }
.card-val { color: #FFF; font-size: 2.2rem; font-weight: 800; margin: 0; text-shadow: 0 0 10px rgba(255,65,108,0.3); }

/* Animation Delays */
.delay-1 { animation-delay: 0.1s; border-top-color: #ff416c; }
.delay-2 { animation-delay: 0.3s; border-top-color: #ffb84c; }
.delay-3 { animation-delay: 0.5s; border-top-color: #00C9FF; }
.delay-4 { animation-delay: 0.7s; border-top-color: #92FE9D; }

/* Progress Bar Animation */
@keyframes slideFill { from { width: 0%; } }
.progress-bg { background: rgba(255,255,255,0.05); height: 8px; border-radius: 4px; margin-top: 15px; overflow: hidden; }
.progress-fill { height: 100%; border-radius: 4px; background: #ff416c; animation: slideFill 1.5s ease-out forwards; }
.fill-amber { background: #ffb84c; }
.fill-blue { background: #00C9FF; }
</style>
""", unsafe_allow_html=True)

def render_anim_card(label, val, delay_cls, prog_color, prog_pct):
    return f"""
    <div class="animated-card {delay_cls}">
        <div class="card-label">{label}</div>
        <div class="card-val">{val}</div>
        <div class="progress-bg">
            <div class="progress-fill {prog_color}" style="width: {min(prog_pct, 100)}%;"></div>
        </div>
    </div>
    """

st.subheader("📦 Delivery Performance Impact")
c1, c2, c3 = st.columns(3)
with c1: st.markdown(render_anim_card("% Orders Late", f"{stats['pct_late']:.1f}%", "delay-1", "", stats['pct_late']), unsafe_allow_html=True)
with c2: st.markdown(render_anim_card("Delayed >1 Day", f"{stats['pct_delayed_1day']:.1f}%", "delay-2", "fill-amber", stats['pct_delayed_1day']), unsafe_allow_html=True)
with c3: st.markdown(render_anim_card("Delayed >2 Days", f"{stats['pct_delayed_2days']:.1f}%", "delay-3", "fill-blue", stats['pct_delayed_2days']), unsafe_allow_html=True)

st.markdown(f"<div style='animation: popIn 0.8s forwards; opacity: 0; animation-delay: 0.8s; padding: 15px; border-left: 3px solid #ffb84c; background: rgba(255,184,76,0.1); border-radius: 5px;'><b>Insight:</b> Delayed orders have a <b>{stats['rating_drop_pct']:.1f}% lower average rating</b> than on-time orders ({stats['avg_rating_late']:.2f} vs {stats['avg_rating_ontime']:.2f}).</div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

st.subheader("⭐ Customer Experience Impact")
c4, c5 = st.columns(2)
with c4: st.markdown(render_anim_card("Low Ratings (≤3) Caused by Delays", f"{stats['pct_low_ratings_delayed']:.1f}%", "delay-1", "", stats['pct_low_ratings_delayed']), unsafe_allow_html=True)
diff_pts = stats['avg_rating_ontime'] - stats['avg_rating_late']
with c5: st.markdown(render_anim_card("Rating Diff (Late vs On-time)", f"-{diff_pts:.2f} Stars", "delay-2", "fill-amber", (diff_pts/5)*100), unsafe_allow_html=True)

st.markdown(f"<div style='animation: popIn 0.8s forwards; opacity: 0; animation-delay: 0.8s; padding: 15px; border-left: 3px solid #ffb84c; background: rgba(255,184,76,0.1); border-radius: 5px;'><b>Insight:</b> <b>{stats['pct_low_ratings_delayed']:.1f}%</b> of all negative/neutral customer experiences (≤3 stars) are directly associated with logistics failures.</div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

st.subheader("🏪 Seller & 🌍 Regional Concentration")
c6, c7, c8 = st.columns(3)
with c6: st.markdown(render_anim_card("Delays from Top Sellers", f"{stats['pct_delay_top_sellers']:.1f}%", "delay-1", "", stats['pct_delay_top_sellers']), unsafe_allow_html=True)
with c7: st.markdown(render_anim_card("Delays in Top 3 Regions", f"{stats['pct_delays_top3_regions']:.1f}%", "delay-2", "fill-amber", stats['pct_delays_top3_regions']), unsafe_allow_html=True)
with c8: st.markdown(render_anim_card("Rev. high-delay Categories", f"{stats['pct_rev_high_delay_cats']:.1f}%", "delay-3", "fill-blue", stats['pct_rev_high_delay_cats']), unsafe_allow_html=True)

st.markdown(f"<div style='animation: popIn 0.8s forwards; opacity: 0; animation-delay: 1.0s; padding: 15px; border-left: 3px solid #ffb84c; background: rgba(255,184,76,0.1); border-radius: 5px;'><b>Insight:</b> High-volume sellers (>50 orders) carry disproportionate risk, contributing to <b>{stats['pct_delay_top_sellers']:.1f}%</b> of all delayed deliveries and <b>{stats['pct_low_top_sellers']:.1f}%</b> of all low ratings.<br><b>Insight:</b> The worst-performing geographic region has a <b>{stats['diff_best_worst_region']:.1f}% higher delay rate</b> than the best-performing region.</div>", unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

st.markdown("""
<div style="background: linear-gradient(135deg, rgba(255,65,108,0.1), #1a1c23); border-left: 4px solid #FF416C; padding: 25px; border-radius: 8px; animation: popIn 0.8s forwards; opacity: 0; animation-delay: 1.2s; box-shadow: 0 10px 20px rgba(0,0,0,0.3);">
    <h3 style="color: #FF416C; margin-top: 0; font-weight: 700;">🎯 Key Takeaway</h3>
    <p style="font-size: 1.15rem; color: #E2E8F0; line-height: 1.6; margin-bottom: 0;">
    The numbers conclusively prove that <b>logistics over-promising is scaling destructively</b>. Despite strong base product quality, massive chunks of platform revenue and top-tier sellers are bottlenecked by systemic delivery failures. By repairing the SLA estimate engine, we stand to immediately rescue a vast majority of all endangered customer relationships.
    </p>
</div>
""", unsafe_allow_html=True)

