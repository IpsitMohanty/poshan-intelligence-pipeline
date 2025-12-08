# analytics/correlations.py

import pandas as pd

def correlation_report(df: pd.DataFrame, columns: list, top_n: int = 10):
    """
    Print strongest positive and negative correlations among given columns.
    Also exports the pairwise list.
    """
    sub = df[columns].dropna()
    corr = sub.corr()

    pairs = []
    for i, c1 in enumerate(columns):
        for j in range(i+1, len(columns)):
            c2 = columns[j]
            r = corr.loc[c1, c2]
            pairs.append((c1, c2, r))

    pairs_sorted = sorted(pairs, key=lambda x: abs(x[2]), reverse=True)

    print("\n=== Strongest correlations (absolute) ===")
    for c1, c2, r in pairs_sorted[:top_n]:
        direction = "positive" if r > 0 else "negative"
        print(f"{c1} ↔ {c2}: r = {r:.3f} ({direction})")

    # Export
    out = pd.DataFrame(pairs, columns=["Indicator_A", "Indicator_B", "Correlation"])
    out.to_csv("correlation_pairs.csv", index=False)

    print("\n[Saved] correlation_pairs.csv")

    return corr
