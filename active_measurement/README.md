## One folder per time step t_i
**All dates are in UTC.**

### Predicting Counts - Wenlong / Max
1. Input
   1. `<model_dir>/model_final.pth`
   2. deployment scope: stations, years and days, minute window
2. Under `active_measurement`, run `python launch_deploy.py`.
   1. Downloading radar data and rendering arrays (do this once and cache)
   2. Detection with the current detector checkpoint `<model_dir>/model_final.pth`
   3. Tracking
   4. Per-sweep counting
3. Under `active_measurement`, run `python sweep_count_to_day_count.py --model_dir <model_dir> --sweep_counts_dir <sweep_count_dir> --day_count_dir day_counts`.
   1. Aggregate per-sweep counts to per-day counts
      ```
        station,year,month,day,count
        SSSS,YYYY,MM,DD,C
      ```
4. Output files: `<model_dir>/day_counts/day_counts_SSSS_YYYYMMDD_YYYYMMDD.csv`

### Estimation - Jinlin
1. Input files
   1. **unlabeled_station_days_predicted_counts.csv**
2. Steps
   1. Generate a proposal distribution
   2. Sample station-days
   3. Annotate sampled station-days (simulate with all_stations_v2_screened)
   4. Run estimation
   5. Update the unlabeled/labeled sets
3. Output files
   1. **labeled_station_days.json**
   2. __*unlabeled_station_days.json*__ &rarr; save to the t_{i+1} folder

### Finetuning - Max
This doesn't need to be done every time step.
1. Input files
   1. **labeled_station_days.json**
2. Steps
   1. Finetuning / ensembling
   2. Evaluation on a held-out set of station-days
3. Output files
   1. __*detector checkpoint*__ &rarr; save to the t_{i+1} folder

