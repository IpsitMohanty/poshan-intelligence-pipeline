from cubes.district_cube import build_district_cube

folder = r"D:\poshan_intelligence\data\2025-11"

cube = build_district_cube(folder)

print("\n=== CUBE PREVIEW ===")
print(cube.head())

cube.to_csv("district_cube_2025_11.csv", index=False)
print("\nCube exported as district_cube_2025_11.csv")
