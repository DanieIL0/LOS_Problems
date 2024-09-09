import os
from config import VIDEO_DIR, RESULTS_DIR, ROSBAG_DATA_PATH
from rosbag_processing import process_rosbag_files
from video_processing import cut_video_segments

os.makedirs(RESULTS_DIR, exist_ok=True)
segments_to_cut = process_rosbag_files(ROSBAG_DATA_PATH)

# Debugging
# print(f"Segments to cut: {segments_to_cut}")

# Leads to error if empty
if segments_to_cut:
    cut_video_segments(segments_to_cut, VIDEO_DIR, RESULTS_DIR)
else:
    print("No segments found")
