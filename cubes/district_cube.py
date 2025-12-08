import os
import pandas as pd

from etl.gm_0_5 import analyze_gm_0_5
from etl.gm_5_6 import analyze_gm_5_6
from etl.anaemia import analyze_anaemia
from etl.lbw import analyze_lbw
from etl.gwg import analyze_gwg
from etl.adolescent_girls import analyze_adolescent_girls
from etl.measuring_efficiency import analyze_me
from etl.home_visit import analyze_home_visit
from etl.snp import analyze_snp
from etl.awc_summary import analyze_awc_summary


# ---------------------------------------------------
# Helper to standardize columns for district-level merges
# ---------------------------------------------------
def standardize_columns(df):
    df = df.copy()
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("__", "_")
    )
    return df


def clean_district(df):
    df = standardize_columns(df)

    # District column must exist
    if "district" not in df.columns:
        raise KeyError("The dataset does not contain a 'district' column after cleaning.")

    # Standardize district names
    df["district"] = (
        df["district"]
        .astype(str)
        .str.strip()
        .str.title()
        .str.replace("–", "-")
        .str.replace("  ", " ")
    )

    return df


# ---------------------------------------------------
# Build Cube
# ---------------------------------------------------
def build_district_cube(month_folder):
    print("\n=== Building District Intelligence Cube ===")

    # Get list of available cleaned CSV files dynamically
    files = {f.lower(): os.path.join(month_folder, f) for f in os.listdir(month_folder)}

    # Mapping cleaned filenames to analyses
    paths = {
        "gm_0_5": files.get("(0_to_5_years)_growth_monitoring_11_2025.csv".lower()),
        "gm_5_6": files.get("(5_to_6_years)_growth_monitoring_11_2025.csv".lower()),
        "anaemia": files.get("anaemia_11_2025.csv".lower()),
        "lbw": files.get("low_birth_weight_11_2025.csv".lower()),
        "gwg": files.get("gestational_weight_gain_report_11_2025.csv".lower()),
        "ag": files.get("adolescent_girls_(14_18_years)_11_2025.csv".lower()),
        "me": files.get("measuring_efficiency_children_0_to_6_years_11_2025.csv".lower()),
        "hv": files.get("home_visit_11_2025.csv".lower()),
        "snp": files.get("snp_projections_12_2025.csv".lower()),
        "awc": files.get("awc_11_2025.csv".lower()),
    }

    # Load and clean datasets
    dfs = {
        "gm_5_6": clean_district(analyze_gm_5_6(paths["gm_5_6"])),
        "gm_0_5": clean_district(analyze_gm_0_5(paths["gm_0_5"])),
        "anaemia": clean_district(analyze_anaemia(paths["anaemia"])),
        "lbw": clean_district(analyze_lbw(paths["lbw"])),
        "gwg": clean_district(analyze_gwg(paths["gwg"])),
        "ag": clean_district(analyze_adolescent_girls(paths["ag"])),
        "me": clean_district(analyze_me(paths["me"])),
        "hv": clean_district(analyze_home_visit(paths["hv"])),
        "snp": clean_district(analyze_snp(paths["snp"])),
        "awc": clean_district(analyze_awc_summary(paths["awc"])),
    }

    # Start merging on district
    cube = dfs["gm_5_6"]

    for key, df in dfs.items():
        if key == "gm_5_6":
            continue
        print(f"Merging {key} …")
        cube = cube.merge(df, on="district", how="left")

    print("\n=== District Intelligence Cube Built Successfully ===")
    return cube
