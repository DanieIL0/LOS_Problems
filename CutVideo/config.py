import os

# for a segment in sec
MIN_DURATION = 2

# For missing transformations in segment
THRESHOLD_PERCENTAGE = 80

WINDOW_SIZE = 60

VIDEO_FILES = [
    'VIDEOTESTNFSGLINP_30_4-Room+5_compressed.mp4',
    'VIDEOTESTNFSGLINP_30_4-Room+6_compressed.mp4',
    'VIDEOTESTNFSGLINP_30_4-Room+7_compressed.mp4',
    'VIDEOTESTNFSGLINP_30_4-Room+8_compressed.mp4'
]

TIMEFRAMES = [
    "10:00:00 - 10:21:21", "10:36:43 - 10:46:37", "10:47:16 - 10:47:55", 
    "10:56:04 - 10:56:14", "10:56:17 - 10:56:20", "10:56:23 - 11:13:12", 
    "11:21:32 - 11:21:56", "11:22:34 - 11:22:47", "11:24:27 - 11:25:18", 
    "11:26:33 - 11:26:35", "11:26:37 - 11:26:39", "11:26:41 - 11:35:26"
]

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ROSBAG_DATA_PATH = os.path.join(SCRIPT_DIR, '..', '..', 'ROSbag')
VIDEO_DIR = os.path.join(SCRIPT_DIR, '..', '..')
RESULTS_DIR = os.path.join(SCRIPT_DIR, 'results')