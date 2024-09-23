import os
import pandas as pd
import numpy as np
from bagpy import bagreader
from ..shared.config import TIMEFRAMES, WINDOW_SIZE, THRESHOLD_PERCENTAGE
from ..shared.utils import process_timeframes, is_within_timeframes

def process_rosbag_files(rosbag_folder):
    """
    Processes ROS bag files to identify segments where a specified threshold of missing transformations is exceeded.

    Parameters:
        rosbag_folder (str): Directory containing the ROS bag files.

    Returns:
        list: A list of identified segments where the threshold of missing transformations is exceeded.
    """
    segments = []
    timeframes = process_timeframes(TIMEFRAMES)
    window_size = WINDOW_SIZE
    threshold_missing = THRESHOLD_PERCENTAGE / 100.0 * window_size

    all_timestamps = []
    all_transforms = []
    for rosbag_file in os.listdir(rosbag_folder):
        if rosbag_file.endswith(".bag"):
            rosbag_path = os.path.join(rosbag_folder, rosbag_file)
            b = bagreader(rosbag_path)

            ar_tracking_data = b.message_by_topic('/ARTracking')
            if ar_tracking_data:
                ar_tracking_df = pd.read_csv(ar_tracking_data)
                ar_tracking_df = ar_tracking_df[ar_tracking_df['header.frame_id'] == 'telescopeMarkerTransform']

                timestamps = ar_tracking_df['Time'].astype(float).values
                transforms = ar_tracking_df['pose.position.x'].values

                all_timestamps.extend(timestamps)
                all_transforms.extend(transforms)

    # Analyze the combined data
    start_timestamp = None
    for i in range(len(all_timestamps) - window_size + 1):
        window_data = np.array(all_transforms[i:i + window_size])
        missing_count = np.sum(window_data == 0)

        if missing_count >= threshold_missing:
            if start_timestamp is None:
                start_timestamp = all_timestamps[i]
        else:
            if start_timestamp is not None:
                end_timestamp = all_timestamps[i + window_size - 1]
                if (is_within_timeframes(start_timestamp, timeframes) and
                        is_within_timeframes(end_timestamp, timeframes)):
                    segments.append((start_timestamp, end_timestamp, "merged"))
                start_timestamp = None

    # Handle the case where the last segment extends to the end
    if start_timestamp is not None:
        end_timestamp = all_timestamps[-1]
        if is_within_timeframes(start_timestamp, timeframes):
            segments.append((start_timestamp, end_timestamp, "merged"))

    merged_segments = []
    previous_segment = None

    for segment in segments:
        if previous_segment and segment[0] <= previous_segment[1] + 1:
            merged_segments[-1] = (previous_segment[0], segment[1], "merged")
        else:
            merged_segments.append(segment)
        previous_segment = segment

    print(f"Final segments to cut: {merged_segments}")

    return merged_segments