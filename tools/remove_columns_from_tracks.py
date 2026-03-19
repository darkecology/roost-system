import os

for station in [
    "KBRO", "KCRP", "KEWX", "KHGX",
    "KGRK", "KFWS", "KLCH", "KSHV",
    "KLIX", "KDGX", "KMOB", "KGWX", "KNQA",
    "KLZK", "KSRX", "KTLX", "KVNX", "KICT",
    "KTWX", "KEAX", "KSGF", "KLSX", "KPAH"
]:
    for year in range(2007, 2013):
        # check if a file exists
        scan_file = f"scans_{station}_{year}0601_{year}1231.txt"
        if scan_file not in os.listdir("us_sunrise_v3_old/"):
            continue

        os.system(f'cp us_sunrise_v3_old/{scan_file} drought_2007-2012/')

        tracks_file = f"tracks_{station}_{year}0601_{year}1231.txt"
        with open(f'us_sunrise_v3_old/{tracks_file}', "r") as file:
            lines = file.readlines()
            new_lines = [line.strip() for line in lines]
            assert new_lines[0] == "track_id,filename,from_sunrise,det_score,x,y,r,lon,lat,radius,geo_dist,local_time,n_radar_pixels,n_refAbove40_pixels,n_xcorrAbove0.95_pixels,n_xcorrBelow0.95_refAbove40_pixels", tracks_file
            new_lines = [",".join(line.split(",")[:12]) + "\n" for line in new_lines]  # keep columns until n_radar_pixels
            for i in range(len(lines)):
                assert lines[i].startswith(new_lines[i].strip()), f"{lines[i]}\n{new_lines[i]}"

        with open(f'drought_2007-2012/{tracks_file}', "w") as file:
            file.writelines(new_lines)
