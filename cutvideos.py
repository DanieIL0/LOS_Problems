import os
import sys
from datetime import datetime
import logging
import pytz
from implementation.shared.config import VIDEO_DIR, RESULTS_DIR_VID, ROSBAG_DATA_PATH
from implementation.cut.rosbag_processing import process_telescope_transforms, process_phantom_transforms
from implementation.cut.video_processing import cut_video_segments

LOGS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(LOGS_DIR, exist_ok=True)
current_time = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = f"log_{current_time}.txt"
log_file_path = os.path.join(LOGS_DIR, log_filename)
tz_berlin = pytz.timezone('Europe/Berlin')
old_tz = os.environ.get('TZ', None)
os.environ['TZ'] = 'Europe/Berlin'
print(f"Script started at {current_time}")
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

try:
    os.makedirs(RESULTS_DIR_VID, exist_ok=True)
    segments_to_cut = process_telescope_transforms(ROSBAG_DATA_PATH)
    segments_of_missing_phantom_transform = process_phantom_transforms(ROSBAG_DATA_PATH)

    if segments_to_cut:
        cut_video_segments(segments_to_cut, segments_of_missing_phantom_transform, VIDEO_DIR, RESULTS_DIR_VID)
    else:
        logging.info("No segments found")
except Exception as e:
    logging.error(f"An error occurred: {e}")
finally:
    logging.info("Script ended")
    sys.stdout = old_stdout 
    sys.stderr = old_stderr 
    log_file.close()

    if old_tz is not None:
        os.environ['TZ'] = old_tz
    else:
        del os.environ['TZ']
        
    print(f"Script ended at {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")