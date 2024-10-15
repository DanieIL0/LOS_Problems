import os

"""
Defines various configuration settings for file paths and processing parameters.
"""

CURRENT_DIRECTORY = os.getcwd()
RESULTS_DIR_VID = os.path.join(CURRENT_DIRECTORY, 'cut_videos')
RESULTS_DIR_PLOT = os.path.join(CURRENT_DIRECTORY, 'plots')
FONT_FILE = 'ARIAL.TTF'

TRIAL_DIRS = [
    '210810_animal_trial_01',
    '210824_animal_trial_02',
    '210914_animal_trial_03',
    '210928_animal_trial_04',
    '211012_animal_trial_05',
    '211019_animal_trial_06',
    '211026_animal_trial_07',
    '211102_animal_trial_08',
    '211109_animal_trial_09',
    '211116_animal_trial_10',
    '211123_animal_trial_11',
    '211130_animal_trial_12',
    '211130_animal_trial_13',
    '211207_animal_trial_14',
    '211209_animal_trial_15',
    '211210_animal_trial_16',
    '211214_animal_trial_17',
    '211215_animal_trial_18',
]

DATA_PATHS = [
    {
        'ROSBAG_DATA_PATH': os.path.join(
            CURRENT_DIRECTORY, '..', 'dataset', '03_animal_trial', trial_dir, 'atlas', 'Rosbag'
        ),
        'VIDEO_DIR': os.path.join(
            CURRENT_DIRECTORY, '..', 'dataset', '03_animal_trial', trial_dir, 'atlas', 'VideosCompressed'
        ),
        'LOG_FILE_DIR': os.path.join(
            CURRENT_DIRECTORY, '..', 'dataset', '03_animal_trial', trial_dir, 'atlas', 'Annotations'
        ),
    }
    for trial_dir in TRIAL_DIRS
]

MIN_DURATION = 2
THRESHOLD_PERCENTAGE = 90
WINDOW_SIZE = 60

PADDING_SECONDS = 1.5
PHANTOM_THRESHOLD_PERCENTAGE = 80
PHANTOM_WINDOW_SIZE = 60

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

    '2021-12-07': [  # 14 06:11:27

    ],

    '2021-12-09': [  # 15 7:26:23

    ],

    '2021-12-10': [  # 16 05:32:59

    ],

    '2021-12-14': [  # 17 06:44:20

    ],

    '2021-12-15': [  # 18 07:28:56

    ]
}

OVERLAY_DURATION = 0.5

# Plotting-related configurations
PLOT_FLAG = True  # Set to True if you want to plot during processing
VARIANCE_THRESHOLD = 1e-2
NOISE_THRESHOLD = 0.05
SUBSAMPLING_FACTOR = 50