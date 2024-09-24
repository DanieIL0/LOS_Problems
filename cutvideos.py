import os
from implementation.shared.config import VIDEO_DIR, RESULTS_DIR_VID, ROSBAG_DATA_PATH
from implementation.cut.rosbag_processing import process_telescope_transforms, process_phantom_transforms
from implementation.cut.video_processing import cut_video_segments

os.makedirs(RESULTS_DIR_VID, exist_ok=True)
segments_to_cut = process_telescope_transforms(ROSBAG_DATA_PATH)
segments_of_missing_phantom_transform = process_phantom_transforms(ROSBAG_DATA_PATH)

# Debugging
# print(f"Segments to cut: {segments_to_cut}")

# Leads to error if empty
if segments_to_cut:
    cut_video_segments(segments_to_cut, segments_of_missing_phantom_transform, VIDEO_DIR, RESULTS_DIR_VID)
else:
    print("No segments found")
