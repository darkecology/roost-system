"""Code adapted from Maria Belotti's script"""

from wsrlib import slant2ground
from roosts.utils.counting_util import *
import os, csv, argparse


parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str, required=True)
parser.add_argument('--file', type=str, required=True)
args = parser.parse_args()

with open(os.path.join(args.input_dir, args.file), "r") as f:
    lines = [line.rstrip().split(",") for line in f.readlines()]
    # track_id,filename,from_sunset,det_score,x,y,r,lon,lat,radius,geo_dist,local_time


COUNT_IDX = 3
COUNT_CONFIG = {
    "count_scaling": 1.2, # the detector model predicts boxes that "trace roosts", enlarge to get a bounding box
    "max_height": 5000,  # 5000m: this is and should be much higher than roosts' normal height (~2000m)
    "rcs": 4.519,
    "threshold_corr": 0.95,
    "threshold_linZ": {
        60: 21630891,   # 60dBZ
        40: 216309,     # 40dBZ
    },
}

OUTPUT_DIR = f"{args.input_dir}_with_counts"
os.makedirs(OUTPUT_DIR, exist_ok=True)
f_sweeps = open(os.path.join(OUTPUT_DIR, f"sweeps{COUNT_IDX}{args.file[6:]}"), "w")
title = 'track_id,filename,sweep_idx,sweep_angle,count_scaling,' \
        'n_roost_pixels,n_weather_pixels'
for threshold in COUNT_CONFIG["threshold_linZ"].keys():
    title += f',n_highZ_pixels_{threshold}'
title += f',n_animals'
for threshold in COUNT_CONFIG["threshold_linZ"].keys():
    title += f',n_animals_{threshold}'
title += '\n'
f_sweeps.write(title)


for i in range(1, len(lines)):
    if i % 20 == 0:
        print(i)
    line = lines[i]

    xyr = xyr2geo(
        line[4], line[5], line[6], k=COUNT_CONFIG["count_scaling"]
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
            if height > COUNT_CONFIG["max_height"]:
                break

            output = [
                f"{filename[:4]}{line[-1][:8]}-{line[0]}",  # track_id: SSSSYYYYMMDD-i with local date
                filename,
                f"{sweep_index}",
                f"{sweep_angle:.3f}",
                f"{COUNT_CONFIG['count_scaling']:.3f}",
            ]
            n_highZ_pixels_by_linZ_filter = {dBZ: None for dBZ in COUNT_CONFIG["threshold_linZ"].keys()}
            n_animals_by_linZ_filter = {dBZ: None for dBZ in COUNT_CONFIG["threshold_linZ"].keys()}

            # count animals without dBZ filtering
            n_roost_pixels, n_weather_pixels, _, n_animals_no_linZ_filter = calc_n_animals(
                radar,
                sweep_index,
                xyr,
                COUNT_CONFIG["rcs"],
                threshold_corr=COUNT_CONFIG["threshold_corr"],
            )
            output += [f"{n_roost_pixels}", f"{n_weather_pixels}"]

            # count animals with dBZ filtering
            for i, (dBZ, linZ) in enumerate(COUNT_CONFIG["threshold_linZ"].items()):
                _, _, n_highZ_pixels_by_linZ_filter[dBZ], n_animals_by_linZ_filter[dBZ] = calc_n_animals(
                    radar,
                    sweep_index,
                    xyr,
                    COUNT_CONFIG["rcs"],
                    threshold_corr=COUNT_CONFIG["threshold_corr"],
                    threshold_linZ=linZ,
                )

            # output
            output += [f"{n_highZ_pixels_by_linZ_filter[dBZ]}" for dBZ in COUNT_CONFIG["threshold_linZ"].keys()]
            output += [f"{n_animals_no_linZ_filter:.3f}"]
            output += [f"{n_animals_by_linZ_filter[dBZ]:.3f}" for dBZ in COUNT_CONFIG["threshold_linZ"].keys()]
            f_sweeps.write(",".join(output) + "\n")

        except Exception as error:
            print(f"line {i} sweep {sweep_index} has an error in counting animals: ", error)
            continue
