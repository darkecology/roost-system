import boto3
import botocore
from datetime import datetime, timedelta
import re
import os.path
import errno    
import os
import sys

####################################
# Helpers
####################################
def datetime_range(start=None, end=None, delta=timedelta(minutes=1), inclusive=True):
    """Construct a generator for a range of dates
    
    Args:
        from_date (datetime): start time
        to_date (datetime): end time
        delta (timedelta): time increment
        inclusive (bool): whether to include the 
    
    Returns:
        Generator object
    """
    t = start or datetime.now()
    
    if inclusive:
        keep_going = lambda s, e: s <= e
    else:
        keep_going = lambda s, e: s < e

    while keep_going(t, end):
        yield t
        t = t + delta
    return

def s3_key(t, station):
    """Construct (prefix of) s3 key for NEXRAD file
   
    Args:
        t (datetime): timestamp of file
        station (string): station identifier

    Returns:
        string: s3 key, excluding version string suffic
        
    Example format:
            s3 key: 2015/05/02/KMPX/KMPX20150502_021525_V06.gz
        return val: 2015/05/02/KMPX/KMPX20150502_021525
    """
    
    key = '%04d/%02d/%02d/%04s/%04s%04d%02d%02d_%02d%02d%02d' % (
        t.year, 
        t.month, 
        t.day, 
        station, 
        station,
        t.year,
        t.month,
        t.day,
        t.hour,
        t.minute,
        t.second
    )
    
    return key

def s3_prefix(t, station=None):
    prefix = '%04d/%02d/%02d' % (t.year, t.month, t.day)
    if station is not None:
        prefix = prefix + '/%04s/%04s' % (station, station)
    return prefix

def parse_key(key):
    path, key = os.path.split(key)
    vals = re.match('(\w{4})(\d{4}\d{2}\d{2}_\d{2}\d{2}\d{2})(\.?\w+)', key)
    (station, timestamp, suffix) = vals.groups()
    t = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
    return t, station    

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


####################################
# AWS setup
####################################
bucket = boto3.resource('s3', region_name='us-east-2').Bucket('noaa-nexrad-level2')
darkecology_bucket = boto3.resource('s3', region_name='us-east-2').Bucket('cajun-batch-test')

def get_station_day_scan_keys(start_time, end_time, station, stride_in_minutes=3, thresh_in_minutes=3):

    prefix = s3_prefix(start_time, station)
    start_key = s3_key(start_time, station)
    end_key = s3_key(end_time, station)

    # Get s3 objects for this day
    objects = bucket.objects.filter(Prefix=prefix)

    # Select keys that fall between our start and end time
    keys = [o.key for o in objects
                if o.key >= start_key
                and o.key <= end_key]
    if not keys:
        return []

    # iterate by time and select the appropriate scans
    times = list(datetime_range(start_time, end_time, timedelta(minutes=stride_in_minutes)))
    time_thresh = timedelta(minutes=thresh_in_minutes)

    selected_keys = []
    current_idx = 0
    for t in times:
        t_current, _ = parse_key(keys[current_idx])

        while current_idx + 1 < len(keys):
            t_next, _ = parse_key(keys[current_idx + 1])
            if abs(t_current - t) < abs(t_next - t):
                break
            t_current = t_next
            current_idx += 1

        if abs(t_current - t) <= time_thresh:
            selected_keys.append(keys[current_idx])

    return selected_keys


def download_scans(keys, data_dir):
    for key in keys:
        # Download files
        local_file = os.path.join(data_dir, key)
        local_path, filename = os.path.split(local_file)
        mkdir_p(local_path)

        # Download file if we don't already have it
        if not os.path.isfile(local_file):
            bucket.download_file(key, local_file)

    return local_file