"""Code adapted from Maria Belotti's script"""

from wsrlib import slant2ground
from roosts.utils.counting_util import *
import os, csv, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str, required=True)
parser.add_argument('--file', type=str, required=True)

parser.add_argument('--counting_method_idx', type=int, required=True)
parser.add_argument('--threshold', type=int, default=216309, # 40dbZ
                    help="dbZ threshold for not counting a pixel as animals")
parser.add_argument('--dualpol', type=bool, default=False)
args = parser.parse_args()

count_cfg = {
    "count_scaling": 1.2, # the detector model predicts boxes that "trace roosts", enlarge to get a bounding box
    "max_height": 5000,  # 5000m: this is and should be much higher than roosts' normal height (~2000m)
    "rcs": 4.519,
    "threshold": args.threshold,
}

INPUT_DIR = args.input_dir
with open(os.path.join(INPUT_DIR, args.file), "r") as f:
    lines = [line.rstrip().split(",") for line in f.readlines()]
    # track_id,filename,from_sunset,det_score,x,y,r,lon,lat,radius,geo_dist,local_time

OUTPUT_DIR = f"{args.input_dir}_with_counts"
os.makedirs(OUTPUT_DIR, exist_ok=True)
f_sweeps = open(os.path.join(OUTPUT_DIR, f"sweeps{args.counting_method_idx}{args.file[6:]}"), "w")
f_sweeps.write(
    f'track_id,filename,sweep_idx,sweep_angle,count_scaling,'
    f'n_roost_pixels,n_overthresh_pixels,n_animals\n'
)

for i in range(1, len(lines)):
    if i % 20 == 0:
        print(i)
    line = lines[i]

    xyr = xyr2geo(
        line[4], line[5], line[6], k=count_cfg["count_scaling"]
    )  # geometric offset to radar
    geo_dist = (xyr[0] ** 2 + xyr[1] ** 2) ** 0.5

    filename = line[1]
    try:
        # https://github.com/darkecology/pywsrlib/blob/master/wsrlib/wsrlib.py#L161
        radar = read_http(filename)
    except Exception as error:
        print(f"line {i} has an error in loading the radar scan: ", error)
        continue

    try:
        sweep_indexes, sweep_angles = get_unique_sweeps(radar)
    except Exception as error:
        print(f"line {i} has an error in getting unique sweeps: ", error)
        continue

    for sweep_index, sweep_angle in sorted(zip(sweep_indexes, sweep_angles), key=lambda x: x[1]):
        try:
            _, height = slant2ground(geo_dist, sweep_angle)
            if height > count_cfg["max_height"]:
                break

            n_roost_pixels, n_overthresh_pixels, n_animals = calc_n_animals(
                radar, sweep_index, xyr, count_cfg["rcs"], count_cfg["threshold"], args.dualpol
            )

            f_sweeps.write(
                ",".join([
                    f"{filename[:4]}{line[-1][:8]}-{line[0]}", # SSSSYYYYMMDD-i with local date
                    filename,
                    f"{sweep_index}", f"{sweep_angle:.3f}",
                    f"{count_cfg['count_scaling']:.3f}",

                    f"{n_roost_pixels}",
                    f"{n_overthresh_pixels}",
                    f"{n_animals:.3f}"
                ]) + "\n"
            )
        except Exception as error:
            print(f"line {i} sweep {sweep_index} has an error in counting animals: ", error)
            continue
