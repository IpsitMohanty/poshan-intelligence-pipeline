import pandas as pd
from analytics.correlations import correlation_report

CUBE = "district_cube_2025_11.csv"

cols = [
    "stunting_total_pct",
    "underweight_total_pct",
    "measurement_efficiency",
    "stunting_total_pct_0_5",
    "underweight_total_pct_0_5",
    "measurement_coverage_pct_0_5",
    "lbw_rate_pct",
    "pw_anaemia_rate",
    "ag_anaemia_rate",
    "visit_coverage_pct",
    "optimum_wg_latest_pct"
]


def main():
    df = pd.read_csv(CUBE)
    correlation_report(df, cols)

if __name__ == "__main__":
    main()
