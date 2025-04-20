import os, time

NUM_CPUS = 7
os.system(f"export MKL_NUM_THREADS={NUM_CPUS}")
os.system(f"export OPENBLAS_NUM_THREADS={NUM_CPUS}")
os.system(f"export OMP_NUM_THREADS={NUM_CPUS}")


EXP_DIRS = ["KAPX", "KBUF", "KCLE", "KDLH", "KDTX", "KGRB", "KGRR", "KLOT", "KMKX", "KTYX", "KIWX"]
EXP_DIRS = [f"/mnt/nfs/home/wenlongzhao/work1/counting-labels/roost_counts/{s}_10" for s in EXP_DIRS]
EXP_DIRS += ["/mnt/nfs/home/wenlongzhao/work1/counting-labels/roost_counts/init"]

for EXP_DIR in EXP_DIRS:
    INPUT_DIR = f"{EXP_DIR}/bounding_boxes"
    SLURM_LOGS = f"{EXP_DIR}/slurm_counting_logs/"
    os.makedirs(SLURM_LOGS, exist_ok=True)

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
        --time=2-00:00:00 \
        2_count.sh \
        --input_dir {INPUT_DIR} --file {file}'''

        os.system(cmd)
        time.sleep(1)