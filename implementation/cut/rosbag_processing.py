import os
import pandas as pd
import numpy as np
import logging
from bagpy import bagreader
from ..shared.config import (
    TIMEFRAMES,
    WINDOW_SIZE,
    THRESHOLD_PERCENTAGE,
    PHANTOM_WINDOW_SIZE,
    PHANTOM_THRESHOLD_PERCENTAGE,
)
from ..shared.utils import process_timeframes, is_within_timeframes

def extract_marker_transforms(rosbag_folder, marker_frame_id):
    """
    Extracts the transforms for a specified marker from ROS bag files.

    Parameters:
        rosbag_folder (str): Directory containing the ROS bag files.
        marker_frame_id (str): The frame ID of the marker to extract transforms for.

    Returns:
        tuple: Two lists containing timestamps and transforms.
    """
    all_timestamps = []
    all_transforms = []
    for rosbag_file in os.listdir(rosbag_folder):
        if rosbag_file.endswith(".bag"):
            rosbag_path = os.path.join(rosbag_folder, rosbag_file)
            logging.info(f"Processing rosbag file: {rosbag_path}")
            try:
                b = bagreader(rosbag_path)

                if '/ARTracking' not in b.topics:
                    logging.warning(f"/ARTracking topic not found in {rosbag_file}. Skipping this rosbag.")
                    continue

                ar_tracking_data = b.message_by_topic('/ARTracking')
                if not ar_tracking_data or not os.path.exists(ar_tracking_data):
                    logging.warning(f"No data found for /ARTracking in {rosbag_file}. Skipping this rosbag.")
                    continue

                ar_tracking_df = pd.read_csv(ar_tracking_data, index_col=False)

                if ar_tracking_df.empty:
                    logging.warning(f"Empty dataframe for /ARTracking in {rosbag_file}. Skipping this rosbag.")
                    continue

                if 'header.frame_id' not in ar_tracking_df.columns:
                    logging.warning(f"'header.frame_id' column not found in {ar_tracking_data}. Skipping this rosbag.")
                    continue

                marker_df = ar_tracking_df[ar_tracking_df['header.frame_id'] == marker_frame_id]

                if marker_df.empty:
                    logging.warning(f"No data found for marker '{marker_frame_id}' in {rosbag_file}. Skipping this rosbag.")
                    continue

                marker_df = marker_df[pd.to_numeric(marker_df['Time'], errors='coerce').notnull()]
                marker_df['Time'] = marker_df['Time'].astype(float)

                if 'pose.position.x' not in marker_df.columns:
                    logging.warning(f"'pose.position.x' column not found in marker data from {rosbag_file}. Skipping this rosbag.")
                    continue

                marker_df = marker_df[pd.to_numeric(marker_df['pose.position.x'], errors='coerce').notnull()]
                marker_df['pose.position.x'] = marker_df['pose.position.x'].astype(float)

                timestamps = marker_df['Time'].values
                transforms = marker_df['pose.position.x'].values

                all_timestamps.extend(timestamps)
                all_transforms.extend(transforms)
            except Exception as e:
                logging.error(f"Error processing {rosbag_file}: {str(e)}. Skipping this rosbag.")
                continue
    return all_timestamps, all_transforms

def identify_missing_segments(all_timestamps, all_transforms, window_size, threshold_percentage, timeframes):
    """
    Identifies segments where the percentage of missing transformations exceeds the threshold.

    Parameters:
        all_timestamps (list): List of timestamps.
        all_transforms (list): List of transforms.
        window_size (int): The size of the window to check for missing transforms.
        threshold_percentage (float): The percentage threshold for missing transforms.
        timeframes (list): List of timeframes to consider.

    Returns:
        list: A list of identified segments where the threshold of missing transformations is exceeded.
    """
    threshold_missing = threshold_percentage / 100.0 * window_size
    segments = []
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

    return segments

def merge_segments(segments):
    """
    Merges overlapping or consecutive segments.

    Parameters:
        segments (list): List of segments to merge.

    Returns:
        list: A list of merged segments.
    """
    merged_segments = []
    previous_segment = None

    for segment in segments:
        if previous_segment and segment[0] <= previous_segment[1] + 1:
            merged_segments[-1] = (previous_segment[0], segment[1], "merged")
        else:
            merged_segments.append(segment)
        previous_segment = segment

    return merged_segments

def process_telescope_transforms(rosbag_folder):
    """
    Processes telescope marker transforms to identify segments with missing data.

    Parameters:
        rosbag_folder (str): Directory containing the ROS bag files.

    Returns:
        list: A list of telescope segments where missing data exceeds the threshold.
    """
    timeframes = process_timeframes(TIMEFRAMES)
    window_size = WINDOW_SIZE
    threshold_percentage = THRESHOLD_PERCENTAGE

    all_timestamps, all_transforms = extract_marker_transforms(rosbag_folder, 'telescopeMarkerTransform')
    segments = identify_missing_segments(all_timestamps, all_transforms, window_size, threshold_percentage, timeframes)
    merged_segments = merge_segments(segments)
    logging.info(f"Telescope segments: {merged_segments}")
    return merged_segments

def process_phantom_transforms(rosbag_folder):
    """
    Processes phantom marker transforms to identify segments with missing data.

    Parameters:
        rosbag_folder (str): Directory containing the ROS bag files.

    Returns:
        list: A list of phantom segments where missing data exceeds the threshold.
    """
    timeframes = process_timeframes(TIMEFRAMES)
    window_size = PHANTOM_WINDOW_SIZE
    threshold_percentage = PHANTOM_THRESHOLD_PERCENTAGE

    all_timestamps, all_transforms = extract_marker_transforms(rosbag_folder, 'phantomMarkerTransform')
    segments = identify_missing_segments(all_timestamps, all_transforms, window_size, threshold_percentage, timeframes)
    merged_segments = merge_segments(segments)
    logging.info(f"Phantom segments: {merged_segments}")
    return merged_segments