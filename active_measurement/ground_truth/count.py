"""Code adapted from Maria Belotti's script"""

from wsrlib import slant2ground, read_http
from roosts.utils.counting_util import *
import os, csv, argparse


parser = argparse.ArgumentParser()
parser.add_argument('--input_dir', type=str, required=True)
parser.add_argument('--file', type=str, required=True)
args = parser.parse_args()

with open(os.path.join(args.input_dir, args.file), "r") as f:
    lines = [line.rstrip().split(",") for line in f.readlines()]

# 0-4   track_id,filename,from_sunrise,det_score,x,
# 5-9   y,r,lon,lat,radius,
# 10-14 local_time,station,date,time,local_date,
# 15-19 length,tot_score,avg_score,viewed,user_labeled,
# 20-23 label,original_label,notes,day_notes
title = lines[0]
assert title[14] == "local_date" and title[20] == "label"
lines = [
    line.rstrip().split(",") for line in lines[1:]
    if (
        int(line[14][4:8]) > 600 and int(line[14][4:8]) < 1100 and # June to Oct
        line[20] in ["swallow-roost", "weather-roost", "unknown-noise-roost", "AP-roost", "bad-track"]  # roosts
    )
]

PP_CFG = {
    "geosize":          300000,
}

# counting config
CNT_CFG = {
    "count_scaling":    1.2,    # the detector model predicts boxes that trace roosts, enlarge to get bounding boxes
    "max_height":       5000,   # 5000m: this is and should be much higher than roosts' normal height (~2000m)
    "rcs":              get_bird_rcs(54),
    "xcorr_threshold":  [       # dual-pol cross correlation threshold
        0.95
    ],
    "linZ_threshold":   {
        40: 216309,             # 40dBZ -> 216309 in the linear scale
    }                           # linear scale threshold above which we consider reflectivity to be too high,
}

OUTPUT_DIR = f"sweep_counts"
os.makedirs(OUTPUT_DIR, exist_ok=True)
station_day_range = "_".join(args.file.split("_")[2:])
f_sweep = open(os.path.join(OUTPUT_DIR, f"sweeps_{station_day_range}"), "w")

f_sweep.write(
    'track_id,filename,sweep_idx,sweep_angle,count_scaling,n_roost_pixels'
)
for xcorr_threshold in CNT_CFG["xcorr_threshold"]:
    for linZ_threshold in CNT_CFG["linZ_threshold"].keys():
        assert xcorr_threshold is not np.nan
        f_sweep.write(
            f',n_xcorrAbove{xcorr_threshold}_pixels'
            f',n_xcorrBelow{xcorr_threshold}_refAbove{linZ_threshold}_pixels'
            f',n_xcorrBelow{xcorr_threshold}_refBelow{linZ_threshold}_animals'
        )
f_sweep.write('\n')

# COUNTING! Refer to the count_and_save function in visualizer.py
for i in range(1, len(lines)):
    if i % 20 == 0:
        print(i)
    line = lines[i]

    xyr = xyr2geo(
        line[4], line[5], line[6],
        rmax=PP_CFG["geosize"] / 2,
        k=CNT_CFG["count_scaling"]
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
        sweep_indexes_and_angles = sorted(zip(sweep_indexes, sweep_angles), key=lambda x: x[1])
    except Exception as error:
        print(f"line {i} has an error in getting unique sweeps: ", error)
        continue

    for sweep_index, sweep_angle in sweep_indexes_and_angles:
        try:
            _, height = slant2ground(geo_dist, sweep_angle)
            if height > CNT_CFG["max_height"]:
                break  # exhausted all sweeps within the height threshold, next bounding box

            # for this sweep
            output = [
                # This sweep file is not processed by the UI
                # Directly use SSSSYYYYMMDD-i to match with the UI processed tracks file
                # YYYYMMDD: local date
                f"{filename[:4]}{line[10][:8]}-{line[0]:d}",

                filename,
                f"{sweep_index}",
                f"{sweep_angle:.3f}",
                f"{CNT_CFG['count_scaling']:.3f}",
            ]

            pixel_and_animal_counts = [""]
            for xcorr_threshold in CNT_CFG["xcorr_threshold"]:
                for linZ_threshold in CNT_CFG["linZ_threshold"].keys():
                    (
                        n_roost_pixels,
                        n_xcorrAboveC_pixels,
                        n_xcorrBelowC_refAboveD_pixels,
                        n_xcorrBelowC_refBelowD_animals
                    ) = calc_n_animals(
                        radar,
                        sweep_index,
                        xyr,
                        CNT_CFG["rcs"],
                        xcorr_threshold=xcorr_threshold,
                        linZ_threshold=linZ_threshold
                    )

                    if pixel_and_animal_counts[0] == "":
                        pixel_and_animal_counts[0] = f"{n_roost_pixels}"

                    pixel_and_animal_counts += [
                        f"{n_xcorrAboveC_pixels}",
                        f"{n_xcorrBelowC_refAboveD_pixels}",
                        f"{n_xcorrBelowC_refBelowD_animals:.3f}"
                    ]
            f_sweep.write(",".join(output + pixel_and_animal_counts) + "\n")

        except Exception as error:
            print(f"line {i} sweep {sweep_index} has an error in counting animals: ", error)
            continue
