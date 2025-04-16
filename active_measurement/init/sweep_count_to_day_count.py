"""TODO"""

import pandas as pd
from roosts.utils.summary_utils import *

YEARS = ["2015", "2016", "2017", "2018", "2019"]
MONTHS = set(["06", "07", "08", "09", "10"])
SWEEP_COUNT_DIR = "us_sunrise_v3"
SWEEP_COUNT_KEY = "n_xcorrBelow0.95_refBelow40_animals"

for station in STATIONS:
    for year in YEARS:
        df = pd.read_csv(f"{SWEEPS_DIR}/sweeps_{station}_{year}0101_{year}1231.txt")
        # track_id,filename,sweep_idx,sweep_angle,count_scaling,
        # n_roost_pixels,
        # n_refAbove40_pixels,n_refBelow40_animals,
        # n_xcorrAbove0.95_pixels,n_xcorrBelow0.95_refAbove40_pixels,n_xcorrBelow0.95_refBelow40_animals
        # KAPX20150605-4,KAPX20150605_090714_V06,0,0.483,1.200,2479,69,570.957,278,12,194.823

        # detection_id = track_id + scan affix (UTC time and "_V06")
        df["detection_id"] = df.apply(lambda x: str(x.track_id) + x.filename[12:], axis = 1)

        # Functions should be called in this specific order:
        det_df = summarize_sweeps(df, SWEEP_COUNT_KEY)
        det_df = create_frame_idx(det_df)
        track_df = summarize_tracks(det_df)

        # Create date column:
        track_df["date"] = df.apply(lambda x: x.filename[4:12], axis = 1)

        # Summarize by date with the sum of n_animals:
        daily_df = track_df.groupby("date").n_animals.sum()