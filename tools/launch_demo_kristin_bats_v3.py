"""
Launch one slurm job per station-year for Kristin's bat deployment.

Stations: KVNX, KFDR, KTLX
Years: 2005-2025, all days
Window: 150 min before to 150 min after local sunset

Counting is selected in demo.py by species=bat and model_version=v3
(count_scaling 1.2, max_height 5000 m, rcs 4.519, 40 dBZ).
The experiment name must not match the swallow counting branches
(us_sunrise_v3, drought_2007-2012, debug_v3).
"""
import os
import time

# Config for deploying the system
NUM_CPUS = 7

# Run with TRANSFER_ONLY=1 to resend outputs that were already computed but failed to reach DST_HOST.
TRANSFER_ONLY = os.environ.get("TRANSFER_ONLY", "0") == "1"

# deployment station, start date (inclusive), end date (inclusive)
STATIONS = ["KVNX", "KFDR", "KTLX"]
TIMES = []
for year in range(2005, 2026):
    for (start_date, end_date) in [("0101", "1231")]:
        TIMES.append((str(year)+start_date, str(year)+end_date))
# for transferring outputs from the computing cluster to our server
# STATIONS = ["XXXX"]
# TIMES = [("99990101", "99991201")]

SPECIES = "bat"
SUN_ACTIVITY = "sunset"  # bat activities occur around sunset
MIN_BEFORE = 150
MIN_AFTER = 150

# directory for system outputs: ${OUTPUT_ROOT}/${EXPERIMENT_NAME}
MODEL_VERSION = "v3"
EXPERIMENT_NAME = f"kristin_bats_{MODEL_VERSION}"  # dataset name
OUTPUT_ROOT = f"/mnt/nfs/scratch1/wenlongzhao/roosts_data"
os.makedirs(os.path.join(OUTPUT_ROOT, EXPERIMENT_NAME), exist_ok=True)

# directory for slurm logs
SRC_SLURM = "/mnt/nfs/home/wenlongzhao/work1/roost-system/tools/slurm_logs"

# Config for transferring outputs from the computing cluster to our server
DST_HOST = "doppler.cs.umass.edu"
DST_IMG = "/var/www/html/roost/img"  # dz05 and vr05 jpg images
DST_PRED = "/scratch2/wenlongzhao/roostui/data"  # bounding boxes and counts
DST_ARRAY = "/scratch2/wenlongzhao/RadarNPZ/v0.3.0"  # arrays
DST_OTHERS = "/scratch2/wenlongzhao/roosts_deployment_outputs"  # logs, scans

try:
    assert STATIONS_TIMES
    args_list = STATIONS_TIMES
except:
    args_list = [(s, t[0], t[1]) for s in STATIONS for t in TIMES]
for args in args_list:
    station = args[0]
    start = args[1]
    end = args[2]

    slurm_logs_dir = os.path.join(SRC_SLURM, EXPERIMENT_NAME, station)
    suffix = ".transfer.out" if TRANSFER_ONLY else ".out"  # keep the processing logs intact
    slurm_output = os.path.join(slurm_logs_dir, f"{station}_{start}_{end}{suffix}")
    os.makedirs(slurm_logs_dir, exist_ok=True)

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
    --cpus-per-task={1 if TRANSFER_ONLY else NUM_CPUS} \
    --mem-per-cpu=2000 \
    --time={"1-00:00:00" if TRANSFER_ONLY else "7-00:00:00"} \
    demo.sh \
    {SPECIES} {station} {start} {end} \
    {SUN_ACTIVITY} {MIN_BEFORE} {MIN_AFTER} \
    {OUTPUT_ROOT} {MODEL_VERSION} \
    {EXPERIMENT_NAME} {SRC_SLURM} \
    {DST_HOST} {DST_IMG} {DST_PRED} {DST_ARRAY} {DST_OTHERS} \
    {1 if TRANSFER_ONLY else 0}'''

    os.system(cmd)
    time.sleep(1)
