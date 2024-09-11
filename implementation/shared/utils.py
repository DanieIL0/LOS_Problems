import numpy as np
from datetime import datetime

def is_noisy(data, threshold):
    return np.std(data) > threshold

def smooth_data(data, window_size):
    return data.rolling(window=window_size).mean()

def rescale_data(data):
    return (data - data.min()) / (data.max() - data.min())

def convert_to_timestamp(time_str, reference_date='2021-09-28'):
    datetime_str = f"{reference_date} {time_str}"
    datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    timestamp = int(datetime_obj.timestamp())
    return timestamp

def process_timeframes(timeframes):
    timestamps = []
    for timeframe in timeframes:
        start_time, end_time = timeframe.split(' - ')
        start_timestamp = convert_to_timestamp(start_time)
        end_timestamp = convert_to_timestamp(end_time)
        timestamps.append((start_timestamp, end_timestamp))
    return timestamps
