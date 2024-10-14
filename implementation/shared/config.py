import os

"""
Defines various configuration settings for file paths and processing parameters.
"""

CURRENT_DIRECTORY = os.getcwd()
ROSBAG_DATA_PATH = os.path.join(CURRENT_DIRECTORY, '..', 'ROSbag') 
RESULTS_DIR_VID = os.path.join(CURRENT_DIRECTORY, 'cut_videos')
RESULTS_DIR_PLOT = os.path.join(CURRENT_DIRECTORY, 'plots')
VIDEO_DIR = os.path.join(CURRENT_DIRECTORY, '..', 'Videos')
LOG_FILE_DIR = os.path.join(CURRENT_DIRECTORY, '..', 'Annotations')

LOG_FILES = [
    filename for filename in os.listdir(LOG_FILE_DIR)
    if os.path.isfile(os.path.join(LOG_FILE_DIR, filename)) and filename.endswith('.log')
]

LOG_FILE = ""

if LOG_FILES:
    for log_file in LOG_FILES:
        log_file_path = os.path.join(LOG_FILE_DIR, log_file)
        with open(log_file_path, 'r') as file:
            LOG_FILE += file.read() + "\n"
else:
    concatenated_logs = None

FONT_FILE = 'ARIAL.TTF'

if not os.path.exists(RESULTS_DIR_VID):
    os.makedirs(RESULTS_DIR_VID)

if not os.path.exists(RESULTS_DIR_PLOT):
    os.makedirs(RESULTS_DIR_PLOT)

MIN_DURATION = 2
THRESHOLD_PERCENTAGE = 90
WINDOW_SIZE = 60

PADDING_SECONDS = 1.5
PHANTOM_THRESHOLD_PERCENTAGE = 80
PHANTOM_WINDOW_SIZE = 1

VIDEO_FILES = [
    filename for filename in os.listdir(VIDEO_DIR)
    if os.path.isfile(os.path.join(VIDEO_DIR, filename)) and 'Room' in filename
]

TIMEFRAMES = {
    '2021-08-11': [  # 01 7:45:29
       # "28:36 - 28:39", "29:04 - 30:00"
    ],

    '2021-08-24': [  # 02 10:11:24

    ],

    '2021-09-14': [  # 03 26: 7:13:40; 28: 8:37:34
        
    ],

    '2021-09-28': [  # 04 10:00:08
        "10:00:08 - 10:21:29", "10:36:51 - 10:46:45", "10:47:24 - 10:48:03",
        "10:56:12 - 10:56:22", "10:56:25 - 10:56:28", "10:56:31 - 11:13:20",
        "11:21:40 - 11:22:04", "11:22:42 - 11:22:55", "11:24:35 - 11:25:26",
        "11:26:41 - 11:26:49", "11:26:45 - 11:26:47", "11:26:49 - 11:35:34"
    ],

    '2021-10-12': [  # 05 6:22:42

    ],

    '2021-10-19': [  # 06 7:35:41

    ],

    '2021-10-26': [  # 07 6:51:48

    ],

    '2021-11-02': [  # 08 7:30:17

    ],

    '2021-11-09': [  # 09 5:50:52

    ],

    '2021-11-16': [  # 10 06:05:32

    ],

    '2021-11-23': [  # 11 6:57:58

    ],

    '2021-11-30': [  # 12 5:41:23  13 15:01:55


    ],

    '2021-12-07': [  # 14

    ],

    '2021-12-09': [  # 15

    ],

    '2021-12-10': [  # 16

    ],

    '2021-12-14': [  # 17

    ],

    '2021-12-15': [  # 18

    ]
}

OVERLAY_DURATION = 0.5

# Plotting-related configurations
PLOT_FLAG = True  # Set to True if you want to plot during processing
VARIANCE_THRESHOLD = 1e-2
NOISE_THRESHOLD = 0.05
SUBSAMPLING_FACTOR = 50