import os, time

INPUT_DIR = "texas_bats_v3"  # TODO
COUNTING_METHOD_IDX = 2
THRESHOLD = 216309  # 40dbZ
DUALPOL = False

SLURM_LOGS = f"slurm_logs/"
os.makedirs(SLURM_LOGS, exist_ok=True)

NUM_CPUS = 7
os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")

for file in os.listdir(INPUT_DIR):
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
    --time=4-00:00:00 \
    run.sh \
    --dir {INPUT_DIR} --file {file} \
    --counting_method_idx {COUNTING_METHOD_IDX} \
    --threshold {THRESHOLD} \
    --dualpol {DUALPOL}'''  # TODO

    os.system(cmd)
    time.sleep(1)