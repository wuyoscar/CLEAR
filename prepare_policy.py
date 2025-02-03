import pandas as pd
import requests
import os
from urllib.parse import urlparse
from tqdm import tqdm
from pathlib import Path

def download_pdf(url, base_path, pdf_path):
    """
    url: PDF download URL
    base_path: Base directory (./data/pdf_lga/)
    pdf_path: Relative path/filename from the DataFrame
    """
    try:
        # Construct full save path
        full_save_path = os.path.join(base_path, pdf_path)
        
        # Create directory structure for the file
        os.makedirs(os.path.dirname(full_save_path), exist_ok=True)
        
        # Skip if file already exists
        if os.path.exists(full_save_path):
            print(f"File already exists: {pdf_path}")
            return True
        
        # Download the file
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        # Save the file
        with open(full_save_path, 'wb') as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        
        print(f"Successfully downloaded: {pdf_path}")
        return True
    
    except requests.exceptions.RequestException as e:
        print(f"Error downloading {pdf_path}: {str(e)}")
        return False
    except Exception as e:
        print(f"Error saving {pdf_path}: {str(e)}")
        return False

def download_pdfs_from_df(df, base_path):
    """
    df: DataFrame with 'policyURL' and 'pdf_path' columns
    base_path: Base directory for saving PDFs
    """
    results = []
    for _, row in tqdm(df.iterrows(), total=len(df)):
        try:
            url = row['policyURL']
            pdf_path = row['pdf_path']
            success = download_pdf(url, base_path, pdf_path)
            results.append({
                'pdf_path': pdf_path,
                'policyURL': url,
                'success': success,
                'full_path': os.path.join(base_path, pdf_path) if success else None
            })
        except Exception as e:
            print(f"Error processing row: {e}")
            results.append({
                'pdf_path': pdf_path if 'pdf_path' in locals() else 'unknown',
                'policyURL': url if 'url' in locals() else 'unknown',
                'success': False,
                'full_path': None
            })
    
    return pd.DataFrame(results)

if __name__ == "__main__":
    # Read Excel file
    data_path = "./data/db/db_policies.xlsx"
    base_save_dir = './data/pdf_lga'
    
    try:
        # Read Excel and check required columns
        df = pd.read_excel(data_path)
        required_cols = ['policyURL', 'pdf_path']
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        # Create base directory if it doesn't exist
        os.makedirs(base_save_dir, exist_ok=True)
        
        # Download PDFs
        print(f"Starting downloads for {len(df)} files...")
        results_df = download_pdfs_from_df(df, base_save_dir)
        
        # Save results
        results_path = os.path.join(base_save_dir, 'download_results.xlsx')
        results_df.to_excel(results_path, index=False)
        
        # Print summary
        success_count = results_df['success'].sum()
        print(f"\nDownload Summary:")
        print(f"Total files: {len(df)}")
        print(f"Successfully downloaded: {success_count}")
        print(f"Failed: {len(df) - success_count}")
        print(f"Results saved to: {results_path}")
        
    except Exception as e:
        print(f"Error: {str(e)}")