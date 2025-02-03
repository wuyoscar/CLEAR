import pandas as pd
import os
from pathlib import Path

# Get all xlsx files in data/db directory
db_path = Path("data/db")
excel_files = list(db_path.glob("*.xlsx"))

# Convert each xlsx to csv
for excel_file in excel_files:
    try:
        # Read Excel
        df = pd.read_excel(excel_file)
        
        # Create csv filename (same name, different extension)
        csv_file = excel_file.with_suffix('.csv')
        
        # Save as CSV
        df.to_csv(csv_file, index=False)
        print(f"Converted {excel_file.name} to {csv_file.name}")
        
    except Exception as e:
        print(f"Error converting {excel_file.name}: {e}")