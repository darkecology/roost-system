# We make sure the station days with human screened bounding boxes are the same as those with day_counts

import pandas as pd

STATIONS = ["KAPX", "KBUF", "KCLE", "KDLH", "KDTX", "KGRB", "KGRR", "KLOT", "KMKX", "KTYX", "KIWX"]
# TIMES = [(f"{year}0601", f"{year}1031") for year in range(2015, 2020)]
YEARS = ["2015", "2016", "2017", "2018", "2019"]
DIR = "/mnt/nfs/home/wenlongzhao/work1/counting-labels/roost_counts/ground_truth"

for station in STATIONS:
    for year in YEARS:
        # Load bounding boxes and get station_days
        df = pd.read_csv(f'{DIR}/all_stations_v2_screened/roost_labels_{station}_{year}0601_{year}1231.csv')
        df = df[df['label'].isin(["swallow-roost", "weather-roost", "unknown-noise-roost", "AP-roost", "bad-track"])]
        df = df[df['local_time'].str[4:8].astype(int) > 600]
        df = df[df['local_time'].str[4:8].astype(int) < 1100]

        dates_list_1 = set(sorted(df['local_date'].tolist()))

        # Load day_counts and get station_days
        df = pd.read_csv(f'{DIR}/day_counts/day_counts_{station}_{year}0601_{year}1031.csv')
        df['day'] = df['station_day'].apply(lambda x: int(x[4:]))
        dates_list_2 = set(sorted(df['day'].tolist()))

        # Make sure the two sets are the same
        if dates_list_1 != dates_list_2:
            print(f"Station {station} year {year} has different days between roost_labels and day_counts")
            print(dates_list_1)
            print(dates_list_2)