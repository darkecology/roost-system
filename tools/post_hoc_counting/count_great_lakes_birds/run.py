"""Code adapted from Maria Belotti's script"""

from roosts.utils.counting_util import *
import os, csv, argparse

parser = argparse.ArgumentParser()
parser.add_argument('--station', type=str, required=True)
parser.add_argument('--start_year', type=int, required=True)
parser.add_argument('--n_years', type=int, required=True)
parser.add_argument('--species', type=str, default="purple_martin")
parser.add_argument('--scaling_factor', type=float, default=1.0, help="factor to scale boxes; UI uses 1.2")
args = parser.parse_args()

# get_bird_rcs(54) for purple martins; 4.519 for bats
assert args.species in ["purple_martin", "bat"]
rcs = get_bird_rcs(54) if args.species == "purple_martin" else 4.519
# the index of the sweep where we extract counts
SWEEP_INDEX = 0
# Threshold above which we will consider reflectivity to be too high (in linear scale)
# Sometimes useful to have no threshold, sometimes helpful to cut at 30dbZ
REFLECTIVITY_THRESHOLD = 68402

DIR = "../../data"
for model in ["v2", "v3"]:
    input_dir = os.path.join(DIR, f"all_stations_{model}")
    output_dir = os.path.join(DIR, f"count_all_stations_{model}")
    os.makedirs(output_dir, exist_ok=True)
    
    for year in range(args.start_year, args.start_year + args.n_years):
        if (args.station == "KGRB" and year == 2000) or \
                (args.station == "KDLH" and year == 2000) or \
                (args.station == "KTYX" and year in [2001, 2002, 2003, 2004]):
            continue
        print(f"Now processing {args.station} {year} with model {model}!")
    
        input_file = os.path.join(input_dir, f"tracks_{args.station}_{year}0601_{year}1231.txt")
        output_file = os.path.join(output_dir, f"tracks_{args.station}_{year}0601_{year}1231.txt")
    
        with open(input_file, "r") as f:
            lines = [line.rstrip().split(",") for line in f.readlines()]

        f = open(output_file, "w")
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
        
                # Get the center and the radius of the bbox in pixel coordinates
                px_c, py_c, pr_c = float(line[4]), float(line[5]), float(line[6])
                # Convert the pixel coordinates to cartesian values
                # Change y direction from image to geometric
                detection_coordinates = xyr2geo(px_c, py_c, pr_c, k=args.scaling_factor)
        
                n_animals, _, overthresh_percent, _ = calc_n_animals(
                    radar,
                    SWEEP_INDEX,
                    detection_coordinates,
                    rcs,
                    REFLECTIVITY_THRESHOLD,
                    method="polar"
                )
        
                f.write(",".join(
                    lines[i] + [str(n_animals), str(overthresh_percent) + "\n"]
                ))
        
            except:
                f.write(",".join(lines[i] + ["", "\n"]))
