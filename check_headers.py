from etl.loader import load_file

print("\n=== AWC SUMMARY COLUMN HEADERS ===")
df = load_file("data/2025-11/AWC_11_2025.csv")
for c in df.columns:
    print(c)
