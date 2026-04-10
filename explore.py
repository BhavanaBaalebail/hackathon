import pandas as pd
import os

file_path = '/Users/bhavanabaalebail/Documents/hack/NexaCart Data.xlsx'
print(f"File size: {os.path.getsize(file_path)} bytes")

xls = pd.ExcelFile(file_path)
print(f"Sheet names: {xls.sheet_names}")

for sheet_name in xls.sheet_names:
    df = pd.read_excel(xls, sheet_name=sheet_name)
    print(f"\n--- Sheet: {sheet_name} ---")
    print(f"Shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
