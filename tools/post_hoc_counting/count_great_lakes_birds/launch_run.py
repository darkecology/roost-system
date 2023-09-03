import os, time

NUM_CPUS = 7
os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")

SLURM_LOGS = f"slurm_logs/"
os.makedirs(SLURM_LOGS, exist_ok=True)

STATIONS = [
    "KAPX", "KBUF", "KCLE", "KDLH", "KDTX", "KGRB",
    "KGRR", "KIWX", "KLOT", "KMKX", "KMQT", "KTYX",
]
START_YEARS = range(2000, 2021, 3)
N_YEARS = 3
SPECIES = "purple_martin"
SCALING_FACTOR = 1.0 # factor to scale boxes; UI uses 1.2

for station in STATIONS:
    for start_year in START_YEARS:

        slurm_output = os.path.join(SLURM_LOGS, f"{station}{start_year}-{start_year+2}.out")
        slurm_error = os.path.join(SLURM_LOGS, f"{station}{start_year}-{start_year+2}.err")

        cmd = f'''sbatch \
        --job-name="{station}{start_year}" \
        --output="{slurm_output}" \
        --error="{slurm_error}" \
        --nodes=1 \
        --ntasks=1 \
        --cpus-per-task={NUM_CPUS} \
        --mem-per-cpu=2000 \
        --partition=longq \
        --time=7-00:00:00 \
        run.sbatch \
        --station {station} \
        --start_year {start_year} \
        --n_years {N_YEARS} \
        --species {SPECIES} \
        --scaling_factor {SCALING_FACTOR}'''

        os.system(cmd)
        time.sleep(1)