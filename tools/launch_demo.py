"""
This script can launch many jobs in parallel, each for a station-year and on separate cpus
"""
import os
import time

# Config for deploying the system
NUM_CPUS = 7

# deployment station, start date (inclusive), end date (inclusive)
# specify either
STATIONS = [
    "KBUF"
    # "KCAE",
    # "KCBW",
    # "KGYX",
    # "KBOX",
    # "KOKX",
    # "KCXX",
    # "KENX",
    # "KDIX",
    # "KDOX",
    # "KTYX",
    # "KBGM",
    # "KMHX",
    # "KAKQ",
    # "KLWX",
    # "KCCX",
    # "KLTX",
    # "KRAX",
    # "KBUF",
    # "KPBZ",
    # "KFCX",
    # "KAMX",
    # "KMLB",
    # "KCLX",
    # "KJAX",
    # "KBYX",
]
TIMES = [
    # (f"{year}0601", f"{year}1231") for year in range(2013, 2024)
    (f"{year}0807", f"{year}0808") for year in [2015]
]
# or
# STATIONS_TIMES = [
#     ("KTYX", "20200805", "20200806"),
# ]
# for transferring outputs from the computing cluster to our server
# STATIONS = ["XXXX"]
# TIMES = [("99990101", "99991201")]

SPECIES = "swallow"
SUN_ACTIVITY = "sunrise" # bird activities occur around sunrise
MIN_BEFORE = 30
MIN_AFTER = 90

# directory for system outputs: ${OUTPUT_ROOT}/${EXPERIMENT_NAME}
OUTPUT_ROOT = f"/mnt/nfs/scratch1/wenlongzhao/roosts_data"
MODEL_VERSION = "v3"
EXPERIMENT_NAME = f"us_sunrise_{MODEL_VERSION}_debug" # dataset name

# Config for transferring outputs from the computing cluster to our server
SRC_SLURM = "~/work1/roost-system/tools/slurm_logs"

DST_HOST = "doppler.cs.umass.edu"
DST_IMG = "/var/www/html/roost/img" # dz05 and vr05 jpg images
DST_PRED = "/scratch2/wenlongzhao/roostui/data" # bounding boxes and counts
DST_ARRAY = "/scratch2/wenlongzhao/RadarNPZ/v0.3.0/" # arrays
DST_OTHERS = "/scratch2/wenlongzhao/roosts_deployment_outputs" # logs, scans

try:
    assert STATIONS_TIMES
    args_list = STATIONS_TIMES
except:
    args_list = [(s, t[0], t[1]) for s in STATIONS for t in TIMES]
for args in args_list:
    station = args[0]
    start = args[1]
    end = args[2]
    
    slurm_logs = f"slurm_logs/{EXPERIMENT_NAME}/{station}"
    slurm_output = os.path.join(slurm_logs, f"{station}_{start}_{end}.out")
    os.makedirs(slurm_logs, exist_ok=True)

    os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
    os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
    os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")

    # Now we request cpus via slurm to run the job
    cmd = f'''sbatch \
    --job-name="{station}{start}_{end}" \
    --output="{slurm_output}" \
    --partition=longq \
    --nodes=1 \
    --ntasks=1 \
    --cpus-per-task={NUM_CPUS} \
    --mem-per-cpu=2000 \
    --time=7-00:00:00 \
    demo.sh \
    {SPECIES} {station} {start} {end} \
    {SUN_ACTIVITY} {MIN_BEFORE} {MIN_AFTER} \
    {OUTPUT_ROOT} {MODEL_VERSION} \
    {EXPERIMENT_NAME} {SRC_SLURM} \
    {DST_HOST} {DST_IMG} {DST_PRED} {DST_ARRAY} {DST_OTHERS}'''
    
    os.system(cmd)
    time.sleep(1)