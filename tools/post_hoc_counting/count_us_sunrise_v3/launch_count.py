import os, time

NUM_CPUS = 7
os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")

DATA_DIR = f"predictions"
# TODO: which files in the directory to count
index_start, index_end = 0, 128

SLURM_LOGS = f"slurm_counting_logs"
os.makedirs(SLURM_LOGS, exist_ok=True)

files = sorted([file for file in os.listdir(DATA_DIR) if file.startswith("track")])
for file in files[index_start:index_end]:

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
    --time=2-00:00:00 \
    count.sh \
    --data_dir {DATA_DIR} --file {file}'''

    os.system(cmd)
    time.sleep(1)