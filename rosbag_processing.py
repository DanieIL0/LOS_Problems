import os
import pandas as pd
from bagpy import bagreader
from config import TIMEFRAMES, WINDOW_SIZE, THRESHOLD_PERCENTAGE
from datetime import datetime


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

def is_within_timeframes(timestamp, timeframes):
    for start_time, end_time in timeframes:
        if start_time <= timestamp <= end_time:
            return True
    return False

def process_rosbag_files(rosbag_folder):
    segments = []
    timeframes = process_timeframes(TIMEFRAMES)
    window_size = WINDOW_SIZE
    threshold_missing = THRESHOLD_PERCENTAGE / 100.0 * window_size

    for rosbag_file in os.listdir(rosbag_folder):
        if rosbag_file.endswith(".bag"):
            rosbag_path = os.path.join(rosbag_folder, rosbag_file)
            b = bagreader(rosbag_path)

            ar_tracking_data = b.message_by_topic('/ARTracking')
            if ar_tracking_data:
                ar_tracking_df = pd.read_csv(ar_tracking_data)
                timestamps = ar_tracking_df['Time'].astype(float).values

                start_timestamp = None
                for i in range(len(timestamps) - window_size + 1):
                    window_data = ar_tracking_df['pose.position.x'].iloc[i:i+window_size]
                    missing_count = window_data.eq(0).sum()

                    if missing_count >= threshold_missing:
                        if start_timestamp is None:
                            start_timestamp = timestamps[i]
                    else:
                        if start_timestamp is not None:
                            end_timestamp = timestamps[i + window_size - 1]
                            if (is_within_timeframes(start_timestamp, timeframes) and
                                    is_within_timeframes(end_timestamp, timeframes)):
                                segments.append((start_timestamp, end_timestamp, rosbag_file))
                            start_timestamp = None

                # Handle case where file ends with valid segment
                if start_timestamp is not None:
                    end_timestamp = timestamps[-1]
                    if is_within_timeframes(start_timestamp, timeframes):
                        segments.append((start_timestamp, end_timestamp, rosbag_file))

    # Merge consecutive segments
    merged_segments = []
    previous_segment = None

    for segment in segments:
        if previous_segment:
            if segment[0] <= previous_segment[1] + 2:  # Allow small gap between segments
                merged_segments[-1] = (previous_segment[0], segment[1], segment[2])
            else:
                merged_segments.append(segment)
        else:
            merged_segments.append(segment)
        previous_segment = segment

    # Debugging
    # print(f"Final merged segments to cut: {merged_segments}")

    return merged_segments
