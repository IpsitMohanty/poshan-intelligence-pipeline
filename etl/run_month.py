from pathlib import Path
import os

from utils.files import get_latest_month_folder
from etl.loader import load_all_files
from etl.cleaner import clean_all

# Optional metadata step — safe fallback if file or function does not exist
try:
    from etl.metadata import enrich_metadata
    USE_METADATA = True
except Exception:
    USE_METADATA = False


WAREHOUSE_DIR = Path(os.getenv("WAREHOUSE_DIR", "warehouse"))
RAW_DATA_DIR = Path("data")


def run_etl_for_month(raw_folder: Path, out_folder: Path):
    """
    Core ETL logic:
    1) Loads all monthly CSVs
    2) Cleans & harmonizes
    3) Adds metadata (optional)
    4) Saves cleaned tables to out_folder
    """
    print(f"[ETL] Loading data from: {raw_folder}")
    data_dict = load_all_files(raw_folder)

    print("[ETL] Cleaning + harmonizing...")
    cleaned = clean_all(data_dict)

    if USE_METADATA:
        print("[ETL] Adding metadata...")
        try:
            cleaned = enrich_metadata(cleaned)
        except Exception as e:
            print(f"[ETL] Metadata enrich failed ({e}), skipping.")
    else:
        print("[ETL] No metadata enrich step found — skipping.")

    # Save cleaned output
    out_folder.mkdir(parents=True, exist_ok=True)

    print(f"[ETL] Writing cleaned data to {out_folder}")
    for name, df in cleaned.items():
        df.to_csv(out_folder / f"{name}.csv", index=False)

    print(f"[ETL] Completed ETL for {raw_folder.name}")


def main():
    print("[ETL] Detecting latest month folder...")
    latest_folder = get_latest_month_folder(RAW_DATA_DIR)
    month_tag = latest_folder.name
    print(f"[ETL] Latest month detected: {month_tag}")

    out_folder = WAREHOUSE_DIR / "etl" / month_tag
    run_etl_for_month(latest_folder, out_folder)


if __name__ == "__main__":
    main()
