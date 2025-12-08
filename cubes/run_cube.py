from pathlib import Path
import os
import pandas as pd

from utils.files import get_latest_month_folder
from cubes.district_cube import build_district_cube

WAREHOUSE_DIR = Path(os.getenv("WAREHOUSE_DIR", "warehouse"))


def main():
    etl_root = WAREHOUSE_DIR / "etl"

    print("[CUBE] Detecting latest ETL output month...")
    latest_etl_folder = get_latest_month_folder(etl_root)
    month_tag = latest_etl_folder.name
    print(f"[CUBE] Latest ETL month: {month_tag}")

    print(f"[CUBE] Building district cube using {latest_etl_folder}")
    cube_df = build_district_cube(str(latest_etl_folder))

    # Where cube output will be stored
    cubes_out_dir = WAREHOUSE_DIR / "cubes"
    cubes_out_dir.mkdir(parents=True, exist_ok=True)

    out_file = cubes_out_dir / f"district_cube_{month_tag}.csv"

    cube_df.to_csv(out_file, index=False)
    print(f"[CUBE] Cube exported: {out_file}")


if __name__ == "__main__":
    main()
