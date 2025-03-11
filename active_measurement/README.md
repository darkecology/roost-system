## One folder per time step t_i
**All dates are in UTC.**

### Predicting Counts - Wenlong / Max
1. Input files
   1. **unlabeled_station_days.json**
      ```python
        ["SSSSYYYYMMDD"]
      ```
   2. **detector checkpoint**
2. Steps:
   1. Downloading and rendering (do this once and cache)
   2. Detection (with the current detector checkpoint)
   3. Tracking
   4. Bird count estimation
3. Output files
   1. **unlabeled_station_days_predicted_counts.csv**
      ```
        station,year,month,day,count
        SSSS,YYYY,MM,DD,C
      ```
      
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

