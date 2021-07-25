import os
import time

NUM_CPUS = 7
# station, start date (inclusive), end date (inclusive)
# deployment
STATIONS = ["KEWX"]
TIMES = [("20160320", "20161130"), ("20170320", "20171130"),]
SUN_ACTIVITY = "sunset"
MIN_BEFORE = 20
MIN_AFTER = 60
# directory for system outputs
EXPERIMENT_NAME = "bat" # all_station_v1
DATA_ROOT = f"/mnt/nfs/scratch1/wenlongzhao/roosts_data/{EXPERIMENT_NAME}"


ARGS = [(s, t[0], t[1]) for s in STATIONS for t in TIMES]
for args in ARGS:
    station = args[0]
    start = args[1]
    end = args[2]
    
    slurm_logs = f"slurm_logs/{EXPERIMENT_NAME}/{station}"
    slurm_output = os.path.join(slurm_logs, f"{station}_{start}_{end}.out")
    slurm_error = os.path.join(slurm_logs, f"{station}_{start}_{end}.err")
    os.makedirs(slurm_logs, exist_ok=True)

    os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
    os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
    os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")

    cmd = f'''sbatch \
    --job-name="{station}{start}_{end}" \
    --output="{slurm_output}" \
    --error="{slurm_error}" \
    --nodes=1 \
    --ntasks=1 \
    --cpus-per-task={NUM_CPUS} \
    --mem-per-cpu=2000 \
    --partition=longq \
    --time=2-00:00:00 \
    demo.sbatch \
    --station {station} --start {start} --end {end} \
    --sun_activity {SUN_ACTIVITY} --min_before {MIN_BEFORE} --min_after {MIN_AFTER} \
    --data_root {DATA_ROOT}'''
    
    os.system(cmd)
    time.sleep(1)