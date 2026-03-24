"""
There are 1573 tracks files (from 2013 to 2023 from 143 stations) to recount.
On swarm, we can launch 128 longq jobs in parallel and queue another many longq jobs (at least 370+).
"""

import os, time


INDEX_START, INDEX_END = 1530, 1560  # TODO: file indexes to count birds


NUM_CPUS = 7
os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")

DATA_DIR = "/mnt/nfs/work1/sheldon/wenlongzhao/csv_predictions/us_sunrise_v3_2013-2023_no_counts"
files = sorted([file for file in os.listdir(DATA_DIR) if file.startswith("track")])
print(f"There are {len(files)} tracks files to count")

OUTPUT_DIR = "/mnt/nfs/work1/sheldon/wenlongzhao/csv_predictions/us_sunrise_v3_2013-2023_counts"
os.makedirs(OUTPUT_DIR, exist_ok=True)
SLURM_LOGS = "/mnt/nfs/work1/sheldon/wenlongzhao/csv_predictions/us_sunrise_v3_2013-2023_slurm_counting_logs"
os.makedirs(SLURM_LOGS, exist_ok=True)

for file in files[INDEX_START:INDEX_END]:

    station, year = file.split("_")[1], file.split("_")[2][:4]
    slurm_output = os.path.join(SLURM_LOGS, f"{file}.out")

    cmd = f'''sbatch \
    --job-name="{station}{year}" \
    --output="{slurm_output}" \
    --nodes=1 \
    --ntasks=1 \
    --cpus-per-task={NUM_CPUS} \
    --mem-per-cpu=2000 \
    --partition=longq \
    --time=3-00:00:00 \
    count.sh \
    --data_dir {DATA_DIR} --file {file} --output_dir {OUTPUT_DIR}'''

    os.system(cmd)
    time.sleep(1)