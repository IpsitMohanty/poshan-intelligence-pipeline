import pandas as pd
from analytics.correlations import correlation_report

CUBE = "district_cube_2025_11.csv"

cols = [
    "Stunting_Total_%",
    "Underweight_Total_%",
    "Measurement_Efficiency",
    "Stunting_Total_Pct_0_5",
    "Underweight_Total_Pct_0_5",
    "Measurement_Coverage_Pct_0_5",
    "LBW_Rate_%",
    "PW_Anaemia_Rate",
    "AG_Anaemia_%",
    "HV_Percentage",
    "Optimum_WG_Latest_%"
]


def main():
    df = pd.read_csv(CUBE)
    correlation_report(df, cols)

if __name__ == "__main__":
    main()
