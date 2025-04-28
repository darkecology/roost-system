# (1) We make sure the jobs were not ended early unexpected,
# i.e., the date range with predicted bounding boxes should be about June 1 to October 31.
# (2) We check the number of station-days with day_counts.
# (3) We also make sure the station days with predicted bounding boxes are the same as those with day_counts.

import pandas as pd

STATIONS = ["KAPX", "KBUF", "KCLE", "KDLH", "KDTX", "KGRB", "KGRR", "KLOT", "KMKX", "KTYX", "KIWX"]
YEARS = ["2015", "2016", "2017", "2018", "2019"]
DIR = "/mnt/nfs/home/wenlongzhao/work1/counting-labels/roost_counts/init"

for station in STATIONS:
    for year in YEARS:
        print(f"Station {station} year {year}")

        # Load bounding boxes and get station_days
        df = pd.read_csv(f'{DIR}/bounding_boxes/tracks_{station}_{year}0601_{year}1031.txt')
        df['day'] = df['local_time'].apply(lambda x: int(x[:8]))
        dates_list_1 = sorted(df['day'].tolist())
        # print(dates_list_1[0], dates_list_1[-1])
        assert abs(int(dates_list_1[0]) - int(year + "0601")) < 5
        assert abs(int(dates_list_1[-1]) - int(year + "1031")) < 5
        dates_list_1 = set(dates_list_1)

        # Load day_counts and get station_days
        df = pd.read_csv(f'{DIR}/day_counts/day_counts_{station}_{year}0601_{year}1031.txt')
        df['day'] = df['station_day'].apply(lambda x: int(x[4:]))
        dates_list_2 = sorted(df['day'].tolist())
        if len(dates_list_2) < 120:
            print(f"{len(dates_list_2)} station_days have day_counts")
            print(dates_list_2)
        dates_list_2 = set(dates_list_2)

        # Make sure the two sets are the same
        if dates_list_1 != dates_list_2:
            print(f"Station {station} year {year} has different days between roost_labels and day_counts")
            print(dates_list_1)
            print(dates_list_2)
            raise ValueError