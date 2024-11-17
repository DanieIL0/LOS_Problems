import os
import sys
from datetime import datetime
import logging
from implementation.shared.config import DATA_PATHS, RESULTS_DIR_VID, TIMEFRAMES
from implementation.cut.rosbag_processing import process_telescope_transforms, process_phantom_transforms
from implementation.cut.video_processing import cut_video_segments
from implementation.shared.utils import process_timeframes

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

processed_timeframes = process_timeframes(TIMEFRAMES)

for trial_data in DATA_PATHS:
    ROSBAG_DATA_PATH = trial_data['ROSBAG_DATA_PATH']
    VIDEO_DIR = trial_data['VIDEO_DIR']
    LOG_FILE_DIR = trial_data.get('LOG_FILE_DIR')
    pretrial = trial_data['pretrial']
    trial_number = trial_data['trial_number']
    trial_type = trial_data['trial_type']

    logging.info(f"Processing trial {trial_number}")

    if not os.path.exists(VIDEO_DIR):
        logging.warning(f"Video directory {VIDEO_DIR} does not exist for trial {trial_number}. Skipping trial.")
        continue

    VIDEO_TYPES = ['Room', 'LapColor', 'AtlasAR']

    VIDEO_FILES = [
        filename for filename in os.listdir(VIDEO_DIR)
        if os.path.isfile(os.path.join(VIDEO_DIR, filename)) and
           any(video_type in filename for video_type in VIDEO_TYPES)
    ]

    if not VIDEO_FILES:
        logging.warning(f"No video files found in {VIDEO_DIR} for trial {trial_number}")
        continue

    if not pretrial and LOG_FILE_DIR and os.path.exists(LOG_FILE_DIR):
        LOG_FILES = [
            filename for filename in os.listdir(LOG_FILE_DIR)
            if os.path.isfile(os.path.join(LOG_FILE_DIR, filename)) and filename.endswith('.log')
        ]

        LOG_FILE_CONTENT = ""

        if LOG_FILES:
            for log_file_name in LOG_FILES:
                log_file_path = os.path.join(LOG_FILE_DIR, log_file_name)
                with open(log_file_path, 'r') as file:
                    LOG_FILE_CONTENT += file.read() + "\n"
        else:
            LOG_FILE_CONTENT = None
    else:
        LOG_FILE_CONTENT = None
        logging.info(f"No annotations available for trial {trial_number}.")

    segments_to_cut = process_telescope_transforms(ROSBAG_DATA_PATH)
    segments_of_missing_phantom_transform = process_phantom_transforms(ROSBAG_DATA_PATH)

    if segments_to_cut:
        cut_video_segments(
            segments_to_cut,
            segments_of_missing_phantom_transform,
            VIDEO_DIR,
            RESULTS_DIR_VID,
            trial_number,
            LOG_FILE_CONTENT,
            VIDEO_FILES,
            pretrial,
            trial_type,
            processed_timeframes
        )
    else:
        logging.info(f"No segments found for trial {trial_number}")


logging.info("Script ended")
logging.shutdown()
sys.stdout = old_stdout
sys.stderr = old_stderr
log_file.close()
print(f"Script ended at {datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")