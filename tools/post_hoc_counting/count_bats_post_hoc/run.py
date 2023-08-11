# Code adapted from Maria Belotti's script

from roosts.utils.counting_util import *
import os, csv, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--file', type=str, required=True)
args = parser.parse_args()

INPUT_DIR = "screened"
OUTPUT_DIR = "screened_with_counts"
# get_bird_rcs(54) for purple martins
# 4.519 for bats
rcs = 4.519
# the index of the sweep where we extract counts
sweep_number = 0
# Threshold above which we will consider reflectivity to be too high (in linear scale)
# Sometimes useful to have no threshold, sometimes helpful to cut at 30dbZ
threshold = 68402

os.makedirs(OUTPUT_DIR, exist_ok=True)
with open(os.path.join(INPUT_DIR, args.file), "r") as f:
    lines = [line.rstrip().split(",") for line in f.readlines()]
f = open(os.path.join(OUTPUT_DIR, args.file), "w")

f.write(
    ",".join(lines[0] + [
        "n_animals",
        "overthresh_percent"  # some pixels are NA since reflectivity is over a threshold
    ]) + "\n"
)
for i in range(1, len(lines)):
    if i % 20 == 0:
        print(i)
    line = lines[i]
    filename = line[1]

    try:
        # https://github.com/darkecology/pywsrlib/blob/master/wsrlib/wsrlib.py#L161
        radar = read_s3(filename)

        # Get the center and the radius of the bbox in pixel coordinates:
        px_c, py_c, pr_c = float(line[4]), float(line[5]), float(line[6])
        # TODO add a scaling factor k = 1.2 to match the UI
        # Convert the pixel coordinates to cartesian values:
        detection_coordinates = image2xy(px_c, py_c, pr_c)

        n_animals, _, overthresh_percent, _ = calc_n_animals(
            radar,
            sweep_number,
            detection_coordinates,
            rcs,
            threshold,
            method="polar"
        )

        f.write(",".join(lines[i] + [
            str(n_animals), str(overthresh_percent)
        ]) + "\n")

    except:
        f.write(",".join(lines[i] + ["", "", ""]) + "\n")
