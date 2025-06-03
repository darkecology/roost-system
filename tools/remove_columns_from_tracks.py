import os

dir = "us_sunrise_v3_1995-2012"
files = [f for f in os.listdir(dir+"_old") if f.startswith("tracks")]
for f in files:
    with open(os.path.join(dir+"_old", f), "r") as file:
        lines = file.readlines()
        new_lines = [line.strip() for line in lines]
        assert new_lines[0] == "track_id,filename,from_sunrise,det_score,x,y,r,lon,lat,radius,geo_dist,local_time,n_radar_pixels,n_refAbove40_pixels,n_xcorrAbove0.95_pixels,n_xcorrBelow0.95_refAbove40_pixels", f
        new_lines = [",".join(line.split(",")[:12]) + "\n" for line in new_lines]
        for i in range(len(lines)):
            assert lines[i].startswith(new_lines[i].strip()), f"{lines[i]}\n{new_lines[i]}"

    with open(os.path.join(dir, f), "w") as file:
        file.writelines(new_lines)
