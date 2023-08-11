import os, time

NUM_CPUS = 7
INPUT_DIR = "screened"
for file in os.listdir(INPUT_DIR):
    station, year = file.split("_")[2], file.split("_")[3][:4]

    slurm_logs = f"slurm_logs/"
    slurm_output = os.path.join(slurm_logs, f"{file}.out")
    slurm_error = os.path.join(slurm_logs, f"{file}.err")
    os.makedirs(slurm_logs, exist_ok=True)

    os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
    os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
    os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")

    cmd = f'''sbatch \
    --job-name="{station}{year}" \
    --output="{slurm_output}" \
    --error="{slurm_error}" \
    --nodes=1 \
    --ntasks=1 \
    --cpus-per-task={NUM_CPUS} \
    --mem-per-cpu=2000 \
    --partition=longq \
    --time=1-00:00:00 \
    run.sbatch \
    --file {file}'''

    os.system(cmd)
    time.sleep(1)