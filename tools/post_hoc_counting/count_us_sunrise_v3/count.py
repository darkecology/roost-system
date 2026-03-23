"""
Post-hoc counting: given existing tracks files (without count columns),
download radar scans, compute counts, and produce:
  (1) updated tracks files with count columns appended
  (2) sweeps files with per-sweep animal counts

Logic follows visualizer.py's count_and_save method.
"""

from wsrlib import slant2ground, read_http
from roosts.utils.counting_util import *
import os, csv, argparse


parser = argparse.ArgumentParser()
parser.add_argument('--data_dir', type=str, required=True,
                    help="directory containing input tracks files (without count columns)")
parser.add_argument('--file', type=str, required=True,
                    help="tracks filename, e.g. tracks_KDOX_20130101_20131231.txt")
parser.add_argument('--output_dir', type=str, required=True,
                    help="directory for output tracks and sweeps files")
args = parser.parse_args()

# Read the input tracks file
with open(os.path.join(args.data_dir, args.file), "r") as f:
    reader = csv.reader(f)
    header = next(reader)
    lines = list(reader)

col_idx = {col: i for i, col in enumerate(header)}

PP_CFG = {
    "geosize":          300000,
}

CNT_CFG = {
    "count_scaling":   1.2,
    "max_height":      5000,
    "rcs":             1,
    "xcorr_threshold": [
        np.nan,
        0.95
    ],
    "linZ_threshold":  {
        40: 216309,
    }
}

##########
# Build output column headers
##########

# Tracks: original columns + scan-wise count columns (from lowest sweep over full region)
tracks_count_columns = ["n_radar_pixels"]
for xcorr_threshold in CNT_CFG["xcorr_threshold"]:
    for linZ_threshold in CNT_CFG["linZ_threshold"].keys():
        if xcorr_threshold is np.nan:
            tracks_count_columns.append(f"n_refAbove{linZ_threshold}_pixels")
        else:
            tracks_count_columns.append(f"n_xcorrAbove{xcorr_threshold}_pixels")
            tracks_count_columns.append(
                f"n_xcorrBelow{xcorr_threshold}_refAbove{linZ_threshold}_pixels"
            )

n_empty_track_counts = len(tracks_count_columns)

# Sweeps: per-sweep per-bounding-box animal counts
sweeps_header_parts = [
    "track_id", "filename", "sweep_idx", "sweep_angle", "count_scaling", "n_roost_pixels"
]
for xcorr_threshold in CNT_CFG["xcorr_threshold"]:
    for linZ_threshold in CNT_CFG["linZ_threshold"].keys():
        if xcorr_threshold is np.nan:
            sweeps_header_parts.append(f"n_refAbove{linZ_threshold}_pixels")
            sweeps_header_parts.append(f"n_refBelow{linZ_threshold}_animals")
        else:
            sweeps_header_parts.append(f"n_xcorrAbove{xcorr_threshold}_pixels")
            sweeps_header_parts.append(
                f"n_xcorrBelow{xcorr_threshold}_refAbove{linZ_threshold}_pixels"
            )
            sweeps_header_parts.append(
                f"n_xcorrBelow{xcorr_threshold}_refBelow{linZ_threshold}_animals"
            )

##########
# Open output files
##########

station_day_range = "_".join(args.file.split("_")[-3:])

f_tracks = open(os.path.join(args.output_dir, f"tracks_{station_day_range}"), "w")
f_tracks.write(",".join(header + tracks_count_columns) + "\n")

f_sweep = open(os.path.join(args.output_dir, f"sweeps_{station_day_range}"), "w")
f_sweep.write(",".join(sweeps_header_parts) + "\n")

##########
# COUNTING — adapted from visualizer.py count_and_save
##########

for i, line in enumerate(lines):
    if i % 100 == 0:
        print(f"Counting line {i}/{len(lines)}...", flush=True)

    track_id = line[col_idx["track_id"]]
    filename = line[col_idx["filename"]]
    local_time = line[col_idx["local_time"]]

    xyr = xyr2geo(
        line[col_idx["x"]], line[col_idx["y"]], line[col_idx["r"]],
        rmax=PP_CFG["geosize"] / 2,
        k=CNT_CFG["count_scaling"]
    )
    geo_dist = (xyr[0] ** 2 + xyr[1] ** 2) ** 0.5

    # Load radar scan
    try:
        radar = read_http(filename)
    except Exception as error:
        print(f"line {i} error loading radar scan: {error}")
        f_tracks.write(",".join(line + [""] * n_empty_track_counts) + "\n")
        continue

    # Get unique sweeps sorted by elevation angle
    try:
        sweep_indexes, sweep_angles = get_unique_sweeps(radar)
        sweep_indexes_and_angles = sorted(
            zip(sweep_indexes, sweep_angles), key=lambda x: x[1]
        )
    except Exception as error:
        print(f"line {i} error getting unique sweeps: {error}")
        f_tracks.write(",".join(line + [""] * n_empty_track_counts) + "\n")
        continue

    # --- Tracks count columns: scan-wise bad pixel counts from the lowest sweep ---
    try:
        sweep_index_lowest, sweep_angle_lowest = sweep_indexes_and_angles[0]
        _, height = slant2ground(geo_dist, sweep_angle_lowest)
        assert height <= CNT_CFG["max_height"]

        scan_wise_counts = [""]
        for xcorr_threshold in CNT_CFG["xcorr_threshold"]:
            for linZ_threshold in CNT_CFG["linZ_threshold"].values():
                (
                    n_radar_pixels,
                    n_xcorrAboveC_pixels,
                    n_xcorrBelowC_refAboveD_pixels,
                    _
                ) = calc_n_animals(
                    radar,
                    sweep_index_lowest,
                    (0, 0, PP_CFG["geosize"] / 2),  # full rendered region
                    CNT_CFG["rcs"],
                    xcorr_threshold=xcorr_threshold,
                    linZ_threshold=linZ_threshold
                )

                if scan_wise_counts[0] == "":
                    scan_wise_counts[0] = f"{n_radar_pixels}"

                if xcorr_threshold is np.nan:
                    scan_wise_counts.append(f"{n_xcorrBelowC_refAboveD_pixels}")
                else:
                    scan_wise_counts.append(f"{n_xcorrAboveC_pixels}")
                    scan_wise_counts.append(f"{n_xcorrBelowC_refAboveD_pixels}")

        f_tracks.write(",".join(line + scan_wise_counts) + "\n")

    except Exception as error:
        print(f"line {i} error counting scan-wise pixels: {error}")
        f_tracks.write(",".join(line + [""] * n_empty_track_counts) + "\n")
        continue

    # --- Sweeps file: per-sweep animal counts within the bounding box ---
    for sweep_index, sweep_angle in sweep_indexes_and_angles:
        try:
            _, height = slant2ground(geo_dist, sweep_angle)
            if height > CNT_CFG["max_height"]:
                break

            output = [
                f"{filename[:4]}{local_time[:8]}-{track_id}",
                filename,
                f"{sweep_index}",
                f"{sweep_angle:.3f}",
                f"{CNT_CFG['count_scaling']:.3f}",
            ]

            pixel_and_animal_counts = [""]
            for xcorr_threshold in CNT_CFG["xcorr_threshold"]:
                for linZ_threshold in CNT_CFG["linZ_threshold"].values():
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

                    if xcorr_threshold is np.nan:
                        pixel_and_animal_counts += [
                            f"{n_xcorrBelowC_refAboveD_pixels}",
                            f"{n_xcorrBelowC_refBelowD_animals:.3f}"
                        ]
                    else:
                        pixel_and_animal_counts += [
                            f"{n_xcorrAboveC_pixels}",
                            f"{n_xcorrBelowC_refAboveD_pixels}",
                            f"{n_xcorrBelowC_refBelowD_animals:.3f}"
                        ]
            f_sweep.write(",".join(output + pixel_and_animal_counts) + "\n")

        except Exception as error:
            print(f"line {i} sweep {sweep_index} error counting animals: {error}")
            continue

f_tracks.close()
f_sweep.close()
print("Done.")
