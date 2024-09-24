import os
import pandas as pd
from bagpy import bagreader
from ..shared.config import ROSBAG_DATA_PATH, RESULTS_DIR_PLOT, TIMEFRAMES
from ..shared.utils import process_timeframes

def extract_data_from_bag():
    """
    Extracts data from ROS bag files and processes AR tracking data within specific timeframes.

    Returns:
        tuple: A summary of the extracted data, and the minimum and maximum timestamps.
    """
    summary_data = []

    timestamps = process_timeframes(TIMEFRAMES)

    min_timestamp = None
    max_timestamp = None

    # Iterate over all .bag files in the folder
    for rosbag_file in os.listdir(ROSBAG_DATA_PATH):
        if rosbag_file.endswith(".bag"):
            rosbag_path = os.path.join(ROSBAG_DATA_PATH, rosbag_file)
            print(f"Processing file: {rosbag_file}")
            b = bagreader(rosbag_path)

            ar_tracking_data = b.message_by_topic('/ARTracking')
            if ar_tracking_data:
                ar_tracking_df = pd.read_csv(ar_tracking_data)
                ar_tracking_output = os.path.join(RESULTS_DIR_PLOT, f'{rosbag_file}_ar_tracking_data.csv')
                ar_tracking_df.to_csv(ar_tracking_output, index=False)
                print(f"Data from /ARTracking saved to {ar_tracking_output}")

                ar_tracking_df['Time'] = ar_tracking_df['Time'].astype(float)

                # Filter data out
                filtered_data = pd.DataFrame()
                for start_timestamp, end_timestamp in timestamps:
                    time_filtered_df = ar_tracking_df[
                        (ar_tracking_df['Time'] >= start_timestamp) & 
                        (ar_tracking_df['Time'] <= end_timestamp)
                    ]
                    filtered_data = pd.concat([filtered_data, time_filtered_df])

                if filtered_data.empty:
                    continue

                current_min_timestamp = filtered_data['Time'].min()
                current_max_timestamp = filtered_data['Time'].max()
                if min_timestamp is None or current_min_timestamp < min_timestamp:
                    min_timestamp = current_min_timestamp
                if max_timestamp is None or current_max_timestamp > max_timestamp:
                    max_timestamp = current_max_timestamp

                summary_data.append({
                    'File': rosbag_file,
                    'Total Points': len(filtered_data),
                    'Total Telescope Points': len(filtered_data[filtered_data['header.frame_id'] == 'telescopeMarkerTransform']),
                    'Total Phantom Points': len(filtered_data[filtered_data['header.frame_id'] == 'phantomMarkerTransform']),
                    'Telescope Missing Percentage': filtered_data['pose.position.x'].eq(0).mean() * 100,
                    'Phantom Missing Percentage': filtered_data['pose.position.x'].eq(0).mean() * 100,
                    'Data Available': True
                })

    return summary_data, min_timestamp, max_timestamp