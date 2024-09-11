import os

CURRENT_DIRECTORY = os.getcwd()
ROSBAG_DATA_PATH = os.path.join(CURRENT_DIRECTORY, '..', 'ROSbag') 
RESULTS_DIR_VID = os.path.join(CURRENT_DIRECTORY, 'cut_videos')
RESULTS_DIR_PLOT = os.path.join(CURRENT_DIRECTORY, 'plots')
VIDEO_DIR = os.path.join(CURRENT_DIRECTORY, '..')

if not os.path.exists(RESULTS_DIR_VID):
    os.makedirs(RESULTS_DIR_VID)

if not os.path.exists(RESULTS_DIR_PLOT):
    os.makedirs(RESULTS_DIR_PLOT)

MIN_DURATION = 2
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

# Plotting-related configurations
PLOT_FLAG = True  # Set to True if you want to plot during processing
VARIANCE_THRESHOLD = 1e-2
NOISE_THRESHOLD = 0.05
SUBSAMPLING_FACTOR = 50
