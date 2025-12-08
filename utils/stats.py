import pandas as pd

def safe_corr(df, method="pearson"):
    return df.corr(method=method).round(3)

def top_bottom(df, column, n=10):
    return df.nlargest(n, column), df.nsmallest(n, column)
