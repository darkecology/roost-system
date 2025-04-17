"""Run this under ground_truth/"""

import os, time

NUM_CPUS = 7
os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")


SLURM_LOGS = f"slurm_logs/"
os.makedirs(SLURM_LOGS, exist_ok=True)

INPUT_DIR = "all_stations_v2_screened"
for file in os.listdir(INPUT_DIR):
    station, year = file.split("_")[2], file.split("_")[3][:4]
    slurm_output = os.path.join(SLURM_LOGS, f"{file}.out")

    cmd = f'''sbatch \
    --job-name="{station}{year}" \
    --output="{slurm_output}" \
    --nodes=1 \
    --ntasks=1 \
    --cpus-per-task={NUM_CPUS} \
    --mem-per-cpu=2000 \
    --partition=longq \
    --time=2-00:00:00 \
    count.sh \
    --input_dir {INPUT_DIR} --file {file}'''

    os.system(cmd)
    time.sleep(1)