import os
import sys
from datetime import datetime
import logging
from implementation.shared.config import VIDEO_DIR, RESULTS_DIR_VID, ROSBAG_DATA_PATH
from implementation.cut.rosbag_processing import process_telescope_transforms, process_phantom_transforms
from implementation.cut.video_processing import cut_video_segments

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
print(f"Script started at {current_time}")
log_filename = f"log_{current_time}.txt"
log_file_path = os.path.join(LOGS_DIR, log_filename)
old_stdout = sys.stdout
old_stderr = sys.stderr

log_file = open(log_file_path, 'a')

sys.stdout = log_file
sys.stderr = log_file 

logging.basicConfig(
    level=logging.INFO,
    stream=log_file,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logging.info("Starting the script") 

os.makedirs(RESULTS_DIR_VID, exist_ok=True)
segments_to_cut = process_telescope_transforms(ROSBAG_DATA_PATH)
segments_of_missing_phantom_transform = process_phantom_transforms(ROSBAG_DATA_PATH)
if segments_to_cut:
    cut_video_segments(segments_to_cut, segments_of_missing_phantom_transform, VIDEO_DIR, RESULTS_DIR_VID)
else:
    logging.info("No segments found")
logging.info("Script ended")
logging.shutdown() 
sys.stdout = old_stdout 
sys.stderr = old_stderr 
log_file.close()
print(f"Script ended at {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")