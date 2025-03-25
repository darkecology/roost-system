import pandas as pd
import numpy as np

def select_detections(x, idx_range):
    '''
    Create range of desired detections, selecting positive frame_idx that are smaller than length of each track:
    Selected detections will be in the format: frame_idx + track_id
    '''
    selected_detections = np.arange(x.dist - idx_range, x.dist + idx_range, 1)
    selected_detections = selected_detections[(selected_detections >= 0) & (selected_detections < x.length)]
    selected_detections = [str(selected_detections[i]) + x.track_id for i in range(len(selected_detections))]

    return selected_detections

def create_frame_idx(df):
    '''
    This function creates a column with an index counting the frames within
    each track. Index will start from 0.

    Parameters
    ----------
        df: a pandas dataframe
            Relies on the dataframe having columns "track_id" and "filename", and only one row per detection.

    Returns
    ----------
        df: a pandas dataframe
            The same dataframe, with a new column "frame_idx".
    '''

    # Sort to make sure the indexes will match the proper detections:
    df.sort_values(by = ["track_id", "filename"], inplace = True)

    track_lengths = df["track_id"].value_counts()
    track_lengths.sort_index(inplace = True)

    # Concatenate lists of counts from 0 to track_length for each track:
    frame_idx = []
    for i in range(track_lengths.shape[0]):
        frame_idx = frame_idx + list(np.arange(0, track_lengths.values[i], 1))

    df["frame_idx"] = frame_idx

    return df

def summarize_sweeps(df, beamwidth = 1):
    '''
    This function will summarize, for each detection, radar sweeps taken across
    multiple elevations. In order to prevent double couting of birds in regions
    sampled twice by two consecutive beams, we bin the sweep elevations into
    bins of beamwidth size. We then take the average of sweeps that fall in the
    same bin. Lastly, we sum counts across all bins.

    Parameters
    ----------
    df: a pandas dataframe
        Each row corresponds to one sweep. Requires the following
        columns: sweep_angle (angle of sweep), detection_id (indicates which
        rows correspond to a single detection), n_animals (count from given sweep)

    beamwidth: float
        Vertical beamwidth in degress of the radar system. For NEXRAD, it's 1°.

    Returns
    -------
    df: a pandas dataframe
        Dataframe inheriting most of the columns from the input, but containing
        a single row per detection. Columns not inherited contain sweep-level
        data.
    '''

    # Create bins of one degree width:
    bins = np.arange(0, 21, beamwidth)

    # Create a column in the dataframe attributing a bin to each row according to real sweep angle:
    df["binned_angle"] = pd.cut(df.sweep_angle, bins)

    # Group by detection ID and angle bin, to get mean count of sweeps in the same bin:
    temp = df.groupby(["detection_id","binned_angle"], as_index = False)["n_animals"].mean()

    # Group by the detection ID to sum count across bins:
    temp = temp.groupby("detection_id", as_index = False)["n_animals"].sum()

    # Create new dataframe with one row per detection:
    df = df.drop_duplicates("detection_id")

    # Remove n_animals column:
    df = df.drop(["n_animals"], axis = 1)

    # Append number of animals per detection:
    df = df.merge(temp, how = "left", on = "detection_id")

    # Remove detection-specific columns:
    df = df.drop(["binned_angle", 'n_roost_pixels', 'n_overthresh_pixels', "sweep_idx"], axis = 1)

    return df

def summarize_tracks(df, idx_range = 2):
    '''
    This function will summarize tracks across detections. It finds the
    detection with a count that is closest to the median count for each track,
    and gets the indexes of the idx_range detections preceding it and after it, as
    long as those indexes are valid (not lower than zero, and not greater than
    track length). Finally, it gets the mean count of the selected detections.

    Parameters
    ----------
    df: a pandas dataframe
        Each row corresponds to a detection. It requires columns track_id,
        frame_idx (index of detections within a track), and n_animals.

    idx_range: integer
        Number of detections before and after the median used to create the
        summary metric.

    Returns
    -------
    subdf: a pandas dataframe
        Dataframe with summarized counts per track, inheriting date and
        local date from the input dataframe.
    '''

    # Create column with length of each track:
    df = df.merge(df.track_id.value_counts().reset_index().rename(columns = {"count":"length"}))

    # For each track, get the closest observed value to the median:
    temp = df.groupby("track_id", as_index = False)["n_animals"].quantile(interpolation = "nearest")
    temp.rename(columns = {"n_animals": "median_count"}, inplace = True)

    # Add median to the dataframe and calculate absolute distance between median and count
    df = df.merge(temp, how = "left", on = "track_id")
    df["dist"] = abs(df["n_animals"] - df["median_count"])

    # Find the detection index of the median (the row for each track group which minimizes the distance):
    median_idx = df.groupby("track_id")["dist"].agg(lambda x: np.argmin(x)).reset_index()

    # Add track length to the median dataframe:
    median_idx["length"] = df.drop_duplicates(subset = "track_id").length.values

    # Select detections according between median_idx and +- idx_range:
    selected_detections = median_idx.apply(select_detections, axis = 1, idx_range = idx_range)

    # Unpack list of lists:
    selected_detections = [item for sublist in selected_detections for item in sublist]
    
    # Merge frame index and track_id to filter selected detections:
    df["frame_idx_track_id"] = df.apply(lambda x: str(x.frame_idx) + x.track_id, axis = 1)

    # Finally select detections in main dataframe and calculate the mean per track_id:
    df = df[df.frame_idx_track_id.isin(selected_detections)]
    temp = df.groupby("track_id", as_index = False).n_animals.mean()

    # Create new dataframe with one row per detection:
    df = df.drop_duplicates("track_id")

    # Remove n_animals column:
    df = df.drop(["n_animals"], axis = 1)

    # Append number of animals per detection:
    df = df.merge(temp, how = "left", on = "track_id")

    # Drop unnecesary columns:
    df = df.drop(['count_scaling', 'frame_idx', 'length', 'median_count', 'dist', 'frame_idx_track_id'], axis = 1)

    return df
