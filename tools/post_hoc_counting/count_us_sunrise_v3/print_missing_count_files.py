import os

NO_COUNTS_DIR = "/mnt/nfs/work1/sheldon/wenlongzhao/csv_predictions/us_sunrise_v3_2013-2023_no_counts"
COUNTS_DIR = "/mnt/nfs/work1/sheldon/wenlongzhao/csv_predictions/us_sunrise_v3_2013-2023_counts"

no_counts_files = set(os.listdir(NO_COUNTS_DIR))
counts_files = set(os.listdir(COUNTS_DIR))

files = sorted([file for file in os.listdir(NO_COUNTS_DIR)])
file_to_index = {f: i for i, f in enumerate(files)}
missing = sorted(no_counts_files - counts_files)

print(f"Files in no_counts: {len(no_counts_files)}")
print(f"Files in counts: {len(counts_files)}")
print(f"Files in no_counts but NOT in counts: {len(missing)}")
for f in missing:
    print(f"  [{file_to_index[f]}] {f}")
