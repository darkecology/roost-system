"""
This script can launch many jobs in parallel, each for a station-year and on separate cpus.
On swarm, we can launch 128 longq jobs in parallel.
Assume we process 11 years from 2013 to 2023.
We can launch 11 stations or 121 station-years in parallel.
In total there are about 143 stations in the US.
Deployment will take about 13 days.

Assume we process 18 years from 1995 to 2012.
We can launch 7 stations or 126 station-years in parallel.
In total there are about 143 stations in the US.
Deployment will take about 21 days.
"""
import os
import time

# Config for deploying the system
NUM_CPUS = 7

# Run with TRANSFER_ONLY=1 to resend outputs that were already computed but failed to reach DST_HOST.
TRANSFER_ONLY = os.environ.get("TRANSFER_ONLY", "0") == "1"

# deployment station, start date (inclusive), end date (inclusive)
# specify either
# STATIONS = ["KTLX", "KCBW", "KCXX", "KGYX", "KTYX", "KBUF", "KENX", "KBGM", "KBOX", "KCCX"]
# STATIONS = ["KDIX", "KLWX", "KDOX", "KAKQ", "KRAX", "KMHX", "KLTX", "KOKX"]
# TIMES = [
#     (f"{year}0601", f"{year}1231") for year in range(1995, 2013)
#     # (f"{year}0815", f"{year}0816") for year in [2018]
# ]
# or
def _years_to_station_times(station, years):
    return [(station, f"{year}0601", f"{year}1231") for year in years]

STATIONS_TIMES = (
    _years_to_station_times("KGRK", list(range(1990, 2007)) + [2024, 2025])
    + _years_to_station_times("KHPX", list(range(1990, 2013)) + [2024, 2025])
    + _years_to_station_times("KSHV", list(range(1990, 2007)) + [2024, 2025])
)
# for only transferring outputs from the computing cluster to our server
# STATIONS = ["XXXX"]
# TIMES = [("99990101", "99991201")]

SPECIES = "swallow"
SUN_ACTIVITY = "sunrise"  # bird activities occur around sunrise
MIN_BEFORE = 60
MIN_AFTER = 90

# directory for system outputs: ${OUTPUT_ROOT}/${EXPERIMENT_NAME}
MODEL_VERSION = "v3"
# Output dataset name (paths / UI). Counting config still uses us_sunrise_v3 settings via demo.py.
EXPERIMENT_NAME = "drought_2007-2012"
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