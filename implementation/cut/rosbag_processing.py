import os
import pandas as pd
import numpy as np
import logging
import pytz
from datetime import datetime
from bagpy import bagreader
from ..shared.config import (
    TIMEFRAMES,
    WINDOW_SIZE,
    THRESHOLD_PERCENTAGE,
    PHANTOM_WINDOW_SIZE,
    PHANTOM_THRESHOLD_PERCENTAGE,
    MIN_DURATION
)
from ..shared.utils import process_timeframes, is_within_timeframes

def get_overlapping_timeframes(segment_start, segment_end, timeframes):
    """
    Returns the overlapping portions of a segment with the timeframes.
    """
    overlaps = []
    for start, end in timeframes:
        overlap_start = max(segment_start, start)
        overlap_end = min(segment_end, end)
        if overlap_start < overlap_end:
            overlaps.append((overlap_start, overlap_end))
    return overlaps

def extract_marker_transforms(rosbag_folder, marker_frame_id):
    """
    Extracts the transforms for a specified marker from ROS bag files.
    """
    all_timestamps = []
    all_transforms = []

    base_rosbag_output_dir = os.path.join(os.getcwd(), 'rosbag')
    os.makedirs(base_rosbag_output_dir, exist_ok=True)
    logging.info(f"Base directory for CSV files: {base_rosbag_output_dir}")
    for rosbag_file in os.listdir(rosbag_folder):
        if rosbag_file.endswith(".bag"):
            rosbag_path = os.path.join(rosbag_folder, rosbag_file)
            logging.info(f"Processing rosbag file: {rosbag_path}")
            try:
                b = bagreader(rosbag_path)
                bag_start_time = b.reader.get_start_time()
                bag_end_time = b.reader.get_end_time()
                local_tz = pytz.timezone('Europe/Berlin')
                bag_start_datetime = datetime.fromtimestamp(bag_start_time, tz=local_tz)
                bag_date_str = bag_start_datetime.strftime('%Y-%m-%d')

                if bag_date_str not in TIMEFRAMES or not TIMEFRAMES[bag_date_str]:
                    logging.info(f"No timeframes for date {bag_date_str}. Skipping this rosbag.")
                    continue
                date_timeframes = {bag_date_str: TIMEFRAMES[bag_date_str]}
                date_timeframes_processed = process_timeframes(date_timeframes)

                earliest_start_time = min(start_time for start_time, _ in date_timeframes_processed)
                latest_end_time = max(end_time for _, end_time in date_timeframes_processed)

                if bag_end_time < earliest_start_time or bag_start_time > latest_end_time:
                    logging.info(f"Rosbag file {rosbag_file} does not overlap with the overall timeframe on {bag_date_str}. Skipping.")
                    continue

                rosbag_name = os.path.splitext(rosbag_file)[0]
                desired_output_dir = os.path.join(base_rosbag_output_dir, rosbag_name)
                os.makedirs(desired_output_dir, exist_ok=True)
                b.datafolder = desired_output_dir

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

                marker_df = marker_df[marker_df['Time'].apply(lambda t: is_within_timeframes(t, date_timeframes_processed))]

                if marker_df.empty:
                    logging.warning(f"No data within timeframes for marker '{marker_frame_id}' in {rosbag_file}. Skipping this rosbag.")
                    continue

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
    Clips segments to fit entirely within timeframes and discards segments shorter than MIN_DURATION.
    """
    threshold_missing = threshold_percentage / 100.0 * window_size
    segments = []
    i = 0
    total_points = len(all_timestamps)
    while i <= total_points - window_size:
        window_timestamps = all_timestamps[i:i + window_size]
        window_transforms = all_transforms[i:i + window_size]
        missing_count = np.sum(np.array(window_transforms) == 0)

        if missing_count >= threshold_missing:
            segment_start = window_timestamps[0]
            segment_end = window_timestamps[window_size - 1]
            j = i + 1
            while j <= total_points - window_size:
                next_window_timestamps = all_timestamps[j:j + window_size]
                next_window_transforms = all_transforms[j:j + window_size]
                next_missing_count = np.sum(np.array(next_window_transforms) == 0)
                if next_missing_count >= threshold_missing:
                    segment_end = next_window_timestamps[window_size - 1]
                    j += 1
                else:
                    break
            i = j
            overlapping_timeframes = get_overlapping_timeframes(segment_start, segment_end, timeframes)
            for overlap_start, overlap_end in overlapping_timeframes:
                segment_duration = overlap_end - overlap_start
                if segment_duration >= MIN_DURATION:
                    segments.append((overlap_start, overlap_end, "merged"))
                    logging.debug(f"Segment added: {overlap_start} to {overlap_end}")
                else:
                    logging.debug(f"Segment discarded (too short): {overlap_start} to {overlap_end}")
        else:
            i += 1

    return segments

def merge_segments(segments):
    """
    Merges overlapping or immediately consecutive segments (no gap allowed).
    """
    if not segments:
        return []

    # Sort segments by start time
    segments.sort(key=lambda x: x[0])
    merged_segments = [segments[0]]

    for current in segments[1:]:
        previous = merged_segments[-1]
        if current[0] <= previous[1]:
            merged_segments[-1] = (previous[0], max(previous[1], current[1]), "merged")
        elif current[0] == previous[1]:
            merged_segments[-1] = (previous[0], current[1], "merged")
        else:
            merged_segments.append(current)

    return merged_segments

def process_telescope_transforms(rosbag_folder):
    """
    Processes telescope marker transforms to identify segments with missing data.
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
    """
    timeframes = process_timeframes(TIMEFRAMES)
    window_size = PHANTOM_WINDOW_SIZE
    threshold_percentage = PHANTOM_THRESHOLD_PERCENTAGE

    all_timestamps, all_transforms = extract_marker_transforms(rosbag_folder, 'phantomMarkerTransform')
    segments = identify_missing_segments(all_timestamps, all_transforms, window_size, threshold_percentage, timeframes)
    merged_segments = merge_segments(segments)
    logging.info(f"Phantom segments: {merged_segments}")
    return merged_segments