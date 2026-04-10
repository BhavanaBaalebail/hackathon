import pandas as pd
import numpy as np

# Load data similarly to dashboard
df = pd.read_csv('nexacart_master_preprocessed.csv')
df['review_score_num'] = pd.to_numeric(df['review_score'], errors='coerce')
if 'delivery_delay_days' not in df.columns:
    df['order_estimated_delivery_date'] = pd.to_datetime(df['order_estimated_delivery_date'], errors='coerce')
    df['order_delivered_customer_date'] = pd.to_datetime(df['order_delivered_customer_date'], errors='coerce')
    df['delivery_delay_days'] = (df['order_delivered_customer_date'] - df['order_estimated_delivery_date']).dt.total_seconds() / (24*3600)
df['delivery_delay_days'].fillna(0, inplace=True)
df['review_score_num'].fillna(df['review_score_num'].median(), inplace=True)
if 'payment_value' not in df.columns: df['payment_value'] = 0.0

# Calculate
df_in = df
total_orders = len(df_in)

delayed_orders = df_in[df_in['delivery_delay_days'] > 0]
ontime_orders = df_in[df_in['delivery_delay_days'] <= 0]

pct_late = (len(delayed_orders) / total_orders) * 100 if total_orders else 0
pct_delayed_1day = (len(df_in[df_in['delivery_delay_days'] > 1]) / total_orders) * 100 if total_orders else 0
pct_delayed_2days = (len(df_in[df_in['delivery_delay_days'] > 2]) / total_orders) * 100 if total_orders else 0

avg_rating_ontime = ontime_orders['review_score_num'].mean()
avg_rating_late = delayed_orders['review_score_num'].mean()
rating_drop_pct = ((avg_rating_ontime - avg_rating_late) / avg_rating_ontime) * 100 if avg_rating_ontime and not pd.isna(avg_rating_ontime) else 0

low_ratings = df_in[df_in['review_score_num'] <= 3]
low_ratings_delayed = low_ratings[low_ratings['delivery_delay_days'] > 0]
pct_low_ratings_delayed = (len(low_ratings_delayed) / len(low_ratings)) * 100 if len(low_ratings) else 0

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

geo_col_local = 'customer_state_full' if 'customer_state_full' in df_in.columns else 'customer_state'
if geo_col_local in df_in.columns:
    region_stats = df_in.groupby(geo_col_local).agg({'delivery_delay_days':lambda x: (x>0).mean()})
    best_region_delay = region_stats['delivery_delay_days'].min() * 100
    worst_region_delay = region_stats['delivery_delay_days'].max() * 100
    diff_best_worst_region = worst_region_delay - best_region_delay
    
    region_delay_counts = df_in.groupby(geo_col_local).agg(delayed_count=('delivery_delay_days', lambda x: (x>0).sum()))
    top_3_delay_regions_count = region_delay_counts.nlargest(3, 'delayed_count')['delayed_count'].sum()
    pct_delays_top3_regions = (top_3_delay_regions_count / total_delayed_count) * 100 if total_delayed_count else 0

if 'product_category_name' in df_in.columns and 'payment_value' in df_in.columns:
    cat_stats = df_in.groupby('product_category_name').agg({'payment_value':'sum', 'delivery_delay_days':lambda x: (x>0).mean()})
    overall_delay_rate = len(delayed_orders) / total_orders if total_orders else 0
    high_delay_cats = cat_stats[cat_stats['delivery_delay_days'] > overall_delay_rate]
    total_rev = cat_stats['payment_value'].sum()
    pct_rev_high_delay_cats = (high_delay_cats['payment_value'].sum() / total_rev) * 100 if total_rev else 0

print(f"pct_late: {pct_late}")
print(f"pct_delayed_1day: {pct_delayed_1day}")
print(f"pct_delayed_2days: {pct_delayed_2days}")
print(f"rating_drop_pct: {rating_drop_pct}")
print(f"avg_rating_ontime: {avg_rating_ontime}")
print(f"avg_rating_late: {avg_rating_late}")
print(f"pct_low_ratings_delayed: {pct_low_ratings_delayed}")
print(f"pct_delay_top_sellers: {pct_delay_top_sellers}")
print(f"pct_low_top_sellers: {pct_low_top_sellers}")
print(f"pct_delays_top3_regions: {pct_delays_top3_regions}")
print(f"diff_best_worst_region: {diff_best_worst_region}")
print(f"pct_rev_high_delay_cats: {pct_rev_high_delay_cats}")

