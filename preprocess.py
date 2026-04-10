import pandas as pd
import numpy as np
import os

from io import StringIO
import sys

class Logger:
    def __init__(self, filename):
        self.terminal = sys.stdout
        self.log = open(filename, "w")
    def write(self, message):
        self.terminal.write(message)
        self.log.write(message)
    def flush(self):
        self.terminal.flush()
        self.log.flush()

# Prepare to write summary
summary_path = '/Users/bhavanabaalebail/Documents/hack/preprocessing_summary.txt'
# We will use explicit file writing for the summary block instead of intercepting stdout
# because the summary has a specific requested layout.

data_dir = '/Users/bhavanabaalebail/Documents/hack'
file_path = os.path.join(data_dir, 'NexaCart Data.xlsx')

summary_lines = []
def log(s):
    print(s)
    summary_lines.append(s)

log("=== FILE DISCOVERY ===")
log(f"Files found in folder: {os.listdir(data_dir)}")
log(f"Loading: {file_path} (Size: {os.path.getsize(file_path)} bytes)\n")

# Load Excel
print("Loading Excel file... this might take a minute.")
xls = pd.ExcelFile(file_path)

sheets = {}
for sheet in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet)
    sheets[sheet] = df
    log(f"* {sheet}: {df.shape}")

print("\n--- Detailed File Discovery (Step 0 & 1) ---")
all_cols = []
keys = set(['order_id', 'customer_id', 'seller_id', 'product_id', 'review_id'])
key_mappings = {}

for sheet, df in sheets.items():
    print(f"\nFilename: {sheet}")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print("First 2 rows:")
    print(df.head(2))
    print(f"Dtypes:\n{df.dtypes}")
    all_cols.extend(list(df.columns))
    
    # Identify keys
    sheet_keys = [col for col in df.columns if col in keys or 'zip_code' in col]
    key_mappings[sheet] = sheet_keys

print("\n--- Key Mapping Report ---")
for sheet, s_keys in key_mappings.items():
    print(f"{sheet}: {s_keys}")

unique_cols = set(all_cols)
print(f"\nTotal unique columns across all files: {len(unique_cols)}")

print("\n--- STEP 2: MERGING ---")
log("\n=== MERGE REPORT ===")

# Base table
master = sheets['orders_dataset'].copy()
log(f"Starting shape (orders): {master.shape}")

# Merge order_items
if 'order_items_dataset' in sheets:
    master = master.merge(sheets['order_items_dataset'], on='order_id', how='left')
    log(f"After merging order_items: {master.shape}")

# Merge products
if 'products_dataset' in sheets:
    master = master.merge(sheets['products_dataset'], on='product_id', how='left')
    log(f"After merging products: {master.shape}")

# Merge customers
if 'customers_dataset' in sheets:
    master = master.merge(sheets['customers_dataset'], on='customer_id', how='left')
    log(f"After merging customers: {master.shape}")

# Merge sellers
if 'sellers_dataset' in sheets:
    master = master.merge(sheets['sellers_dataset'], on='seller_id', how='left')
    log(f"After merging sellers: {master.shape}")

# Merge order_reviews
if 'order_reviews_dataset' in sheets:
    master = master.merge(sheets['order_reviews_dataset'], on='order_id', how='left')
    log(f"After merging order_reviews: {master.shape}")

# Merge order_payments
if 'order_payments_dataset' in sheets:
    master = master.merge(sheets['order_payments_dataset'], on='order_id', how='left')
    log(f"After merging order_payments: {master.shape}")

# Merge geolocation (on customer zip code)
if 'geolocation_dataset' in sheets:
    geo = sheets['geolocation_dataset'].copy()
    # Deduplicate geo by zip to avoid cardinality explosion
    geo = geo.drop_duplicates(subset=['geolocation_zip_code_prefix'])
    master = master.merge(geo, left_on='customer_zip_code_prefix', right_on='geolocation_zip_code_prefix', how='left')
    log(f"After merging geolocation: {master.shape}")
    
log(f"Final master shape: {master.shape}")

# Save raw merged
raw_merged_path = os.path.join(data_dir, 'nexacart_raw_merged.csv')
master.to_csv(raw_merged_path, index=False)
print(f"Saved raw merged to {raw_merged_path}")


print("\n--- STEP 3: DATA CLEANING ---")
log("\n=== MISSING VALUES ===")

# Standardize cols
master.columns = [str(c).lower().replace(' ', '_') for c in master.columns]

# Missing before
missing_before = master.isnull().sum()

# Strip whitespace
for c in master.select_dtypes(include=['object']):
    master[c] = master[c].astype(str).str.strip()
    # Revert 'nan' string back to actual NaN if astype(str) converted it
    master.loc[master[c] == 'nan', c] = np.nan

# Handle missing values
numeric_cols = master.select_dtypes(include=[np.number]).columns
for c in numeric_cols:
    if master[c].isnull().sum() > 0:
        master[c].fillna(master[c].median(), inplace=True)

categorical_cols = master.select_dtypes(include=['object', 'category']).columns
for c in categorical_cols:
    if master[c].isnull().sum() > 0:
        master[c].fillna('Unknown', inplace=True)

# Remove full duplicates
master = master.drop_duplicates()

missing_after = master.isnull().sum()

log("Missing count before -> after cleaning:")
for c in master.columns:
    if missing_before[c] > 0 or missing_after[c] > 0:
        log(f"{c}: {missing_before[c]} -> {missing_after[c]}")


print("\n--- STEP 4: DATE/TIME PROCESSING ---")
date_cols = [c for c in master.columns if 'date' in c or 'timestamp' in c or 'time' in c or '_at' in c]
for c in date_cols:
    if master[c].dtype == 'object' or str(master[c].dtype).startswith('datetime') == False:
        # Ignore if it has 'Unknown' due to filling
        master[c] = pd.to_datetime(master[c], errors='coerce')

# Extract from purchase date
if 'order_purchase_timestamp' in master.columns:
    pur = master['order_purchase_timestamp']
    master['year'] = pur.dt.year
    master['month'] = pur.dt.month
    master['day'] = pur.dt.day
    master['day_of_week'] = pur.dt.dayofweek
    master['hour'] = pur.dt.hour

    master['delivery_time_days'] = (master['order_delivered_customer_date'] - pur).dt.total_seconds() / (24*3600)
    master['estimated_delivery_days'] = (master['order_estimated_delivery_date'] - pur).dt.total_seconds() / (24*3600)
    master['delivery_delay_days'] = (master['order_delivered_customer_date'] - master['order_estimated_delivery_date']).dt.total_seconds() / (24*3600)
    
    master['is_late'] = (master['delivery_delay_days'] > 0).astype(int)

# Handle NaNs from coercion
for c in ['delivery_time_days', 'estimated_delivery_days', 'delivery_delay_days']:
    if c in master.columns:
        master[c].fillna(master[c].median(), inplace=True)


print("\n--- STEP 5: FEATURE ENGINEERING ---")
log("\n=== NEW FEATURES CREATED ===")
engineered_cols = []

if 'order_purchase_timestamp' in master.columns:
    # Handle NaT by converting to an explicit unknown strings or filling it before formatting
    master['order_month_year'] = master['order_purchase_timestamp'].dt.to_period('M').astype(str)
    engineered_cols.append('order_month_year')

if 'delivery_delay_days' in master.columns:
    def categorize_delay(d):
        if d < 0: return 'Early'
        elif d == 0: return 'On Time'
        elif d <= 3: return 'Slightly Late'
        else: return 'Very Late'
    master['delivery_performance_bucket'] = master['delivery_delay_days'].apply(categorize_delay)
    engineered_cols.append('delivery_performance_bucket')

if 'review_score' in master.columns:
    def format_review(s):
        try:
            val = float(s)
            if val >= 4: return 'Positive'
            elif val == 3: return 'Neutral'
            else: return 'Negative'
        except:
            return 'Neutral'
    master['review_sentiment'] = master['review_score'].apply(format_review)
    engineered_cols.append('review_sentiment')

if 'freight_value' in master.columns and 'price' in master.columns:
    master['freight_to_price_ratio'] = master['freight_value'] / master['price'].replace(0, 0.0001)
    engineered_cols.append('freight_to_price_ratio')

if 'payment_value' in master.columns:
    p75 = master['payment_value'].quantile(0.75)
    master['is_high_value'] = (master['payment_value'] > p75).astype(int)
    engineered_cols.append('is_high_value')

if 'seller_id' in master.columns:
    seller_counts = master['seller_id'].value_counts()
    master['seller_order_count'] = master['seller_id'].map(seller_counts)
    engineered_cols.append('seller_order_count')
    
    if 'review_score' in master.columns:
        # Avoid non-numeric review scores
        valid_reviews = master[pd.to_numeric(master['review_score'], errors='coerce').notnull()]
        valid_reviews['review_score_num'] = pd.to_numeric(valid_reviews['review_score'])
        avg_review = valid_reviews.groupby('seller_id')['review_score_num'].mean()
        master['seller_avg_review'] = master['seller_id'].map(avg_review).fillna(master['review_score'].median())
        engineered_cols.append('seller_avg_review')
        
    if 'delivery_delay_days' in master.columns:
        avg_delay = master.groupby('seller_id')['delivery_delay_days'].mean()
        master['seller_avg_delay'] = master['seller_id'].map(avg_delay).fillna(0)
        engineered_cols.append('seller_avg_delay')

if 'customer_id' in master.columns:
    cust_counts = master['customer_id'].value_counts()
    master['customer_order_count'] = master['customer_id'].map(cust_counts)
    master['is_repeat_customer'] = (master['customer_order_count'] > 1).astype(int)
    engineered_cols.extend(['customer_order_count', 'is_repeat_customer'])

if 'customer_state' in master.columns and 'seller_state' in master.columns:
    master['same_state_delivery'] = (master['customer_state'] == master['seller_state']).astype(int)
    engineered_cols.append('same_state_delivery')

for col in engineered_cols:
    log(f"* {col}")

print("\n--- STEP 6: OUTLIER HANDLING ---")
log("\n=== OUTLIERS ===")
outlier_cols = ['price', 'freight_value', 'payment_value']
for c in outlier_cols:
    if c in master.columns:
        q99 = master[c].quantile(0.99)
        outliers = (master[c] > q99).sum()
        log(f"{c}: {outliers} outliers detected (>99th percentile). Capping at {q99:.2f}")
        master[c] = np.where(master[c] > q99, q99, master[c])

if 'delivery_time_days' in master.columns:
    sus_count = (master['delivery_time_days'] > 60).sum()
    log(f"delivery_time_days: {sus_count} outliers detected (>60 days). Flagged as is_suspicious_delivery.")
    master['is_suspicious_delivery'] = (master['delivery_time_days'] > 60).astype(int)

print("\n--- STEP 7: GEOGRAPHIC ENRICHMENT ---")
brazil_states = {
    'AC': 'Acre', 'AL': 'Alagoas', 'AP': 'Amapá', 'AM': 'Amazonas', 'BA': 'Bahia', 
    'CE': 'Ceará', 'DF': 'Distrito Federal', 'ES': 'Espírito Santo', 'GO': 'Goiás', 
    'MA': 'Maranhão', 'MT': 'Mato Grosso', 'MS': 'Mato Grosso do Sul', 'MG': 'Minas Gerais', 
    'PA': 'Pará', 'PB': 'Paraíba', 'PR': 'Paraná', 'PE': 'Pernambuco', 'PI': 'Piauí', 
    'RJ': 'Rio de Janeiro', 'RN': 'Rio Grande do Norte', 'RS': 'Rio Grande do Sul', 
    'RO': 'Rondônia', 'RR': 'Roraima', 'SC': 'Santa Catarina', 'SP': 'São Paulo', 
    'SE': 'Sergipe', 'TO': 'Tocantins'
}
if 'customer_state' in master.columns:
    master['customer_state_full'] = master['customer_state'].map(brazil_states).fillna('Unknown')
    
    st_vol = master['customer_state'].value_counts()
    print("Top 10 States by volume:")
    print(st_vol.head(10))
    
    total_orders = len(master)
    underserved = st_vol[st_vol / total_orders < 0.01].index.tolist()
    master['is_underserved_region'] = master['customer_state'].isin(underserved).astype(int)

if 'customer_city' in master.columns:
    print("\nTop 10 Cities by volume:")
    print(master['customer_city'].value_counts().head(10))

if 'customer_state' in master.columns and 'delivery_delay_days' in master.columns:
    avg_delay_st = master.groupby('customer_state')['delivery_delay_days'].mean()
    master['customer_state_avg_delay'] = master['customer_state'].map(avg_delay_st)


print("\n--- STEP 8: CATEGORICAL ENCODING ---")
cat_enc_cols = ['payment_type', 'product_category_name', 'order_status']
for c in cat_enc_cols:
    if c in master.columns:
        master[f"{c}_enc"] = master[c].astype('category').cat.codes

print("\n--- STEP 9: FINAL OUTPUT & SUMMARY REPORT ---")
# Save final
final_path = os.path.join(data_dir, 'nexacart_master_preprocessed.csv')
master.to_csv(final_path, index=False)
print(f"Saved master preprocessed to {final_path}")

# Calculate KPIs for report
log("\n=== DATA OVERVIEW ===")
if 'order_purchase_timestamp' in master.columns:
    min_d = master['order_purchase_timestamp'].min()
    max_d = master['order_purchase_timestamp'].max()
    log(f"Date range of orders: {min_d} to {max_d}")

if 'customer_unique_id' in master.columns:
    log(f"Total unique customers: {master['customer_unique_id'].nunique()}")
elif 'customer_id' in master.columns:
    log(f"Total unique customers: {master['customer_id'].nunique()}")

if 'seller_id' in master.columns:
    log(f"Total unique sellers: {master['seller_id'].nunique()}")
if 'product_id' in master.columns:
    log(f"Total unique products: {master['product_id'].nunique()}")
if 'product_category_name' in master.columns:
    log(f"Total unique categories: {master['product_category_name'].nunique()}")

log("\n=== BUSINESS KPIs ===")
if 'delivery_delay_days' in master.columns:
    log(f"Average delivery delay in days: {master['delivery_delay_days'].mean():.2f}")
    
if 'is_late' in master.columns:
    # percent late
    log(f"% of late orders: {master['is_late'].mean() * 100:.2f}%")
    
if 'delivery_performance_bucket' in master.columns:
    very_late = (master['delivery_performance_bucket'] == 'Very Late').sum()
    log(f"% of very late orders (>3 days): {100 * very_late / len(master):.2f}%")
    
if 'review_score' in master.columns:
    # Ensure numerical 
    valid_scores = pd.to_numeric(master['review_score'], errors='coerce')
    log(f"Average review score overall: {valid_scores.mean():.2f}")
    
if 'review_sentiment' in master.columns:
    negative = (master['review_sentiment'] == 'Negative').sum()
    log(f"% of negative reviews (score 1-2): {100 * negative / len(master):.2f}%")

if 'product_category_name' in master.columns:
    top5_cat = master['product_category_name'].value_counts().head(5).index.tolist()
    log(f"Top 5 product categories by order volume: {', '.join(top5_cat)}")

if 'customer_state' in master.columns:
    top5_st = master['customer_state'].value_counts().head(5).index.tolist()
    log(f"Top 5 states by order volume: {', '.join(top5_st)}")
    
if 'freight_to_price_ratio' in master.columns:
    log(f"Average freight to price ratio: {master['freight_to_price_ratio'].mean():.4f}")

with open(summary_path, 'w') as f:
    f.write('\n'.join(summary_lines))

print("\nPREPROCESSING COMPLETE \u2713")
