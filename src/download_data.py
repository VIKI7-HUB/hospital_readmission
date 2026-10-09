import os
import urllib.request
import zipfile

import pandas as pd

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
RAW_DIR = os.path.join(DATA_DIR, "raw")

UCI_URL = "https://archive.ics.uci.edu/static/public/296/diabetes+130-us+hospitals+for+years+1999-2008.zip"

def download_and_extract_data():
    """
    Downloads and extracts the UCI Diabetes 130-US Hospitals dataset (1999-2008).
    Returns the file path to diabetic_data.csv.
    """
    os.makedirs(RAW_DIR, exist_ok=True)
    csv_path = os.path.join(RAW_DIR, "diabetic_data.csv")
    
    if os.path.exists(csv_path):
        print(f"[+] Dataset already exists at {csv_path}")
        return csv_path
    
    print("[*] Attempting download via ucimlrepo...")
    try:
        from ucimlrepo import fetch_ucirepo
        diabetes_data = fetch_ucirepo(id=296)
        if diabetes_data is not None and diabetes_data.data is not None:
            X = diabetes_data.data.features
            y = diabetes_data.data.targets
        else:
            raise ValueError("Failed to fetch UCI repository dataset (data is None)")
        
        # Combine into single DataFrame for standard pipeline
        df = pd.concat([X, y], axis=1)
        df.to_csv(csv_path, index=False)
        print(f"[+] Successfully fetched and saved dataset via ucimlrepo ({len(df)} rows)")
        return csv_path
    except Exception as e:  # noqa: BLE001
        print(f"[-] ucimlrepo fetch failed: {e}. Falling back to direct URL download...")
    
    zip_path = os.path.join(RAW_DIR, "dataset_diabetes.zip")
    try:
        print(f"[*] Downloading dataset zip from {UCI_URL}...")
        urllib.request.urlretrieve(UCI_URL, zip_path)
        print("[+] Extracting zip archive...")
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(RAW_DIR)
        
        # Check extracted files
        if not os.path.exists(csv_path):
            # Sometimes inside subfolder dataset_diabetes
            for root, dirs, files in os.walk(RAW_DIR):
                if "diabetic_data.csv" in files:
                    found_path = os.path.join(root, "diabetic_data.csv")
                    os.rename(found_path, csv_path)
                    break
        print(f"[+] Successfully downloaded and extracted dataset to {csv_path}")
        if os.path.exists(zip_path):
            os.remove(zip_path)
        return csv_path
    except Exception as ex:
        raise RuntimeError(f"Failed to download dataset: {ex}") from ex

if __name__ == "__main__":
    download_and_extract_data()
