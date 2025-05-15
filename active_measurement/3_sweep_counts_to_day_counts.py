import pandas as pd
import os
from roosts.utils.count_summary_util import *


MODEL_DIRS = ["init"] # ["ground_truth", "init"]
for station in ["KAPX", "KBUF", "KCLE", "KDLH", "KDTX", "KGRB", "KGRR", "KIWX", "KLOT", "KMKX", "KTYX"]:
    for ckpt_idx in ["10", "20", "30", "40"]:
        MODEL_DIRS.append(f"{station}_{ckpt_idx}")
MODEL_DIRS = [f"/mnt/nfs/home/wenlongzhao/work1/counting-labels/roost_counts/{d}" for d in MODEL_DIRS]

SWEEP_COUNT_KEY = "n_xcorrBelow0.95_refBelow40_animals"
DAY_COUNT_DIR = "day_counts_with_ui_filter"

for model_dir in MODEL_DIRS:
    sweep_file_names = [
        f for f in os.listdir(os.path.join(model_dir, "sweep_counts"))
        if f.startswith("sweeps")
    ]

    for sweep_file_name in sweep_file_names:
        sweep_file_path = os.path.join(model_dir, "sweep_counts", sweep_file_name)
        print("Processing file:", sweep_file_path)
        df = pd.read_csv(sweep_file_path)
        if len(df) == 0:
            print("Empty file, skipping...")
            continue

        # track_id,filename,sweep_idx,sweep_angle,count_scaling,
        # n_roost_pixels,
        # n_refAbove40_pixels,n_refBelow40_animals,
        # n_xcorrAbove0.95_pixels,n_xcorrBelow0.95_refAbove40_pixels,n_xcorrBelow0.95_refBelow40_animals
        # KAPX20150605-4,KAPX20150605_090714_V06,0,0.483,1.200,2479,69,570.957,278,12,194.823
        df = df[["track_id", "filename", "sweep_idx", "sweep_angle", SWEEP_COUNT_KEY]].copy()
        # track_id should be SSSSYYYYMMDD-id, where YYYYMMDD is local date
        # in case the track_id only has a numerical id, we add the local date
        # file name is SSSSYYYYMMDD_HHMMSS_V06, where YYYYMMDD is UTC date
        # here we assume the UTC date is the same as local date and use the file name TODO
        df['track_id'] = df.apply(
            lambda row: row['track_id'] if "-" in str(row['track_id']) else f"{row['filename'][:12]}-{row['track_id']}",
            axis=1
        )

        tracks_file_path = os.path.join(
            model_dir,
            "sweep_counts",
            sweep_file_name.replace("sweeps", "tracks")
        )
        box_df = pd.read_csv(tracks_file_path)
        # similar processing to track_id to the above
        box_df['track_id'] = box_df.apply(
            lambda row: row['track_id'] if "-" in str(row['track_id']) else f"{row['filename'][:12]}-{row['track_id']}",
            axis=1
        )

        # The tracks and sweeps files contain all the detections with at least 0.05 confidence.
        # We apply ui filters and only keep the tracks with:
        #  - At least 2 detections
        #  - At least 1 detection with score at least 0.5
        #  - Average score at least 0.15
        box_df = box_df[box_df["track_id"].groupby(box_df["track_id"]).transform("count") >= 2]
        box_df = box_df[box_df.groupby("track_id")["det_score"].transform("max") >= 0.5]
        box_df = box_df[box_df.groupby("track_id")["det_score"].transform("mean") >= 0.15]
        df = df[df["track_id"].isin(box_df["track_id"])]

        # Aggregate over sweeps for each detection
        # df: track_id,filename,sweep_idx,sweep_angle,SWEEP_COUNT_KEY
        # det_df: track_id,filename,n_animals, where each track_id has few rows
        det_df = summarize_over_sweeps(df, SWEEP_COUNT_KEY)

        # Aggregate over detections for each track
        # track_df: track_id,n_animals, where each track_id has one row
        track_df = summarize_over_detections(det_df)

        # Aggregate tracks by date
        track_df["station_day"] = track_df.apply(lambda x: x.track_id[0:12], axis=1)
        daily_df = track_df.groupby("station_day", as_index=False)["n_animals"].sum()
        daily_df.sort_values(by=["station_day"], inplace=True)

        # save "station_day,n_animals" to csv
        os.makedirs(os.path.join(model_dir, DAY_COUNT_DIR), exist_ok=True)
        daily_df.to_csv(
            os.path.join(
                model_dir,
                DAY_COUNT_DIR,
                sweep_file_name.replace("sweeps", "day_counts")
            ),
            index=False
        )
