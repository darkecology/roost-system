"""
This script deploys a finetuned checkpoint on multiple station-years in parallel on separate cpus.
On swarm, we can launch 128 longq jobs in parallel.
"""
import os
import time

# Config for deploying the system
NUM_CPUS = 7

# deployment station, start date (inclusive), end date (inclusive)
# STATIONS = ["KAPX", "KBUF", "KCLE", "KDLH", "KDTX", "KGRB", "KGRR", "KLOT", "KMKX", "KTYX", "KIWX"]
# TIMES = [(f"{year}0601", f"{year}1031") for year in range(2015, 2020)]
# or
STATIONS_TIMES = [
    ("KAPX", "20150601", "20151031"),
    ("KBUF", "20150601", "20151031"),
    ("KCLE", "20160601", "20161031"),
    ("KDLH", "20150601", "20151031"),
    ("KGRB", "20170601", "20171031"),
    ("KGRB", "20190601", "20191031"),
    ("KMKX", "20150601", "20151031"),
    ("KMKX", "20170601", "20171031"),
    ("KIWX", "20160601", "20161031"),
    ("KIWX", "20170601", "20171031"),
]

SPECIES = "swallow"
SUN_ACTIVITY = "sunrise"  # bird activities occur around sunrise
MIN_BEFORE = 30
MIN_AFTER = 90

OUTPUT_ROOT = f"/mnt/nfs/scratch1/wenlongzhao/roosts_data/active_measurement"

# Config for transferring outputs from the computing cluster to our server
DST_HOST = "doppler.cs.umass.edu"
DST_IMG = "/var/www/html/roost/img"  # dz05 and vr05 jpg images
DST_PRED = "/scratch2/wenlongzhao/roostui/data"  # bounding boxes and counts
DST_OTHERS = "/scratch2/wenlongzhao/roosts_deployment_outputs"  # logs

try:
    assert STATIONS_TIMES
    args_list = STATIONS_TIMES
except:
    args_list = [(s, t[0], t[1]) for s in STATIONS for t in TIMES]

for ckpt_idx in ["20", "30", "40"]:
    for args in args_list:
        station = args[0]
        start = args[1]
        end = args[2]

        MODEL_NAME = f"{station}_{ckpt_idx}"
        os.makedirs(os.path.join(OUTPUT_ROOT, MODEL_NAME), exist_ok=True)  # output_dir

        slurm_logs_dir = f"{MODEL_NAME}/slurm_logs"
        os.makedirs(slurm_logs_dir, exist_ok=True)
        slurm_output = os.path.join(slurm_logs_dir, f"{station}_{start}_{end}.out")

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
        1_deploy.sh \
        {SPECIES} {station} {start} {end} \
        {SUN_ACTIVITY} {MIN_BEFORE} {MIN_AFTER} \
        {OUTPUT_ROOT} {MODEL_NAME} \
        {DST_HOST} {DST_IMG} {DST_PRED} {DST_OTHERS}'''

        os.system(cmd)
        time.sleep(1)