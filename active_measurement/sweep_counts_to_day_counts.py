import pandas as pd
from roosts.utils.count_summary_util import *


MODEL_DIRS = ["ground_truth", "init"]
GREAT_LAKES = ["KAPX", "KBUF", "KCLE", "KDLH", "KDTX", "KGRB", "KGRR", "KIWX", "KLOT", "KMKX", "KMQT", "KTYX"]
for station in GREAT_LAKES:
    MODEL_DIRS.append(f"{station}_10")

SWEEP_COUNT_KEY = "n_xcorrBelow0.95_refBelow40_animals"

for model_dir in MODEL_DIRS:
    file_names = [
        f for f in os.listdir(os.path.join(model_dir, "sweep_counts"))
        if f.startswith("sweeps")
    ]

    for file_name in file_names:
        df = pd.read_csv(file_name)
        # track_id,filename,sweep_idx,sweep_angle,count_scaling,
        # n_roost_pixels,
        # n_refAbove40_pixels,n_refBelow40_animals,
        # n_xcorrAbove0.95_pixels,n_xcorrBelow0.95_refAbove40_pixels,n_xcorrBelow0.95_refBelow40_animals
        # KAPX20150605-4,KAPX20150605_090714_V06,0,0.483,1.200,2479,69,570.957,278,12,194.823
        df = df[["track_id", "filename", "sweep_idx", "sweep_angle", SWEEP_COUNT_KEY]].copy()

        # Aggregate over sweeps for each detection
        # df: track_id,filename,sweep_idx,sweep_angle,SWEEP_COUNT_KEY
        # det_df: track_id,filename,n_animals, where each track_id has few rows
        det_df = summarize_over_sweeps(df, SWEEP_COUNT_KEY)

        # Aggregate over detections for each track
        # track_df: track_id,n_animals, where each track_id has one row
        track_df = summarize_over_detections(det_df)

        # Aggregate tracks by date
        track_df["station_day"] = track_df.apply(lambda x: x.track_id[0:12], axis = 1)
        daily_df = track_df.groupby("station_day", as_index=False)["n_animals"].sum()
        daily_df.sort_values(by=["station_day"], inplace=True)

        # save "station_day,n_animals" to csv
        os.makedirs(os.path.join(model_dir, "day_counts"), exist_ok=True)
        daily_df.to_csv(
            os.path.join(
                model_dir,
                "day_counts",
                file_name.replace("sweeps", "predicted_day_counts")
            )
        )