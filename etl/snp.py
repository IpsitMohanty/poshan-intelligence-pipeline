from etl.loader import load_file
import pandas as pd

def analyze_snp(path: str) -> pd.DataFrame:
    """Analyze SNP projections: SAM, SUW, children distribution, and beneficiary load."""

    print("\n=== SNP Projections Analysis ===")

    df = load_file(path)

    # Standardize columns
    df.columns = (
        df.columns.str.strip()
                  .str.lower()
                  .str.replace(" ", "_")
                  .str.replace("(", "")
                  .str.replace(")", "")
                  .str.replace("-", "_")
                  .str.replace("__", "_")
    )

    df = df.rename(columns={

        "district": "district",

        # beneficiary totals
        "total_beneficiary": "total_beneficiary",
        "total_pw": "total_pw",
        "total_lm": "total_lm",

        # child age groups
        "total_children_6m_to_3yr": "children_6m_3y",
        "total_children_3yr_to_5yr": "children_3y_5y",
        "total_children_5yr_to_6yr": "children_5y_6y",

        # SAM
        "total_sam_children_6m_to_3yr": "sam_6m_3y",
        "total_sam_children_3_yr_to_5_yr": "sam_3y_5y",

        # SUW
        "total_suw_children_6m_to_3yr": "suw_6m_3y",
        "total_suw_children_3yr_to_6yr": "suw_3y_6y",

        # SAM + SUW overlap
        "total_sam_with_suw_children_6m_3y": "sam_suw_6m_3y",
        "total_sam_with_suw_children_3y_5y": "sam_suw_3y_5y",

        # AG
        "adolescent_girls": "total_ag"
    })

    # --- DERIVED INDICATORS ---

    # Total children
    df["children_total"] = (
        df["children_6m_3y"] +
        df["children_3y_5y"] +
        df["children_5y_6y"]
    )

    # SAM totals
    df["sam_total"] = df["sam_6m_3y"] + df["sam_3y_5y"]

    # SUW totals
    df["suw_total"] = df["suw_6m_3y"] + df["suw_3y_6y"]

    # Combined SAM + SUW
    df["sam_suw_total"] = df["sam_suw_6m_3y"] + df["sam_suw_3y_5y"]

    # Risk density indicator
    df["sam_ratio"] = (
        df["sam_total"] / df["children_total"].replace(0, pd.NA)
    ).fillna(0).round(3)

    df["suw_ratio"] = (
        df["suw_total"] / df["children_total"].replace(0, pd.NA)
    ).fillna(0).round(3)

    df["sam_suw_ratio"] = (
        df["sam_suw_total"] / df["children_total"].replace(0, pd.NA)
    ).fillna(0).round(3)

    # Population share indicator (useful at district level)
    df["pw_share_pct"] = (
        df["total_pw"] / df["total_beneficiary"].replace(0, pd.NA)
    ).fillna(0).round(2)

    df["lm_share_pct"] = (
        df["total_lm"] / df["total_beneficiary"].replace(0, pd.NA)
    ).fillna(0).round(2)

    df["ag_share_pct"] = (
        df["total_ag"] / df["total_beneficiary"].replace(0, pd.NA)
    ).fillna(0).round(2)

    df["children_share_pct"] = (
        df["children_total"] / df["total_beneficiary"].replace(0, pd.NA)
    ).fillna(0).round(2)

    # Clean district names
    df["district"] = df["district"].astype(str).str.strip().str.title()

    return df
