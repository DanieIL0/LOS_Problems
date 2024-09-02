import os

current_directory = os.getcwd()
rosbag_folder = os.path.join(current_directory, '..', '..', 'ROSbag')  # Update this line to point to the correct ROSbag folder
results_path = os.path.join(current_directory, 'results')

if not os.path.exists(results_path):
    os.makedirs(results_path)

# Thresholds and settings
variance_threshold = 1e-2
noise_threshold = 0.05
subsampling_factor = 50
plot_flag = True  # Set to True if you want to plot during processing

# Enter timeframes here in hh:mm:ss - hh:mm:ss format
timeframes = [
    "10:00:00 - 10:21:21", "10:36:43 - 10:46:37", "10:47:16 - 10:47:55", 
    "10:56:04 - 10:56:14", "10:56:17 - 10:56:20", "10:56:23 - 11:13:12", 
    "11:21:32 - 11:21:56", "11:22:34 - 11:22:47", "11:24:27 - 11:25:18", 
    "11:26:33 - 11:26:35", "11:26:37 - 11:26:39", "11:26:41 - 11:35:26"
]
