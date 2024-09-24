import numpy as np
from datetime import datetime
import re
import subprocess

def is_noisy(data, threshold):
    """
    Determines if data is noisy based on a standard deviation threshold.
    
    Parameters:
        data (array-like): The data to evaluate.
        threshold (float): The standard deviation threshold for noise.

    Returns:
        bool: True if the data is considered noisy, False otherwise.
    """
    return np.std(data) > threshold

def smooth_data(data, window_size):
    """
    Smoothes the data using a rolling mean.

    Parameters:
        data (pandas.Series): The data to smooth.
        window_size (int): The window size for the rolling mean.

    Returns:
        pandas.Series: Smoothed data.
    """
    return data.rolling(window=window_size).mean()

def rescale_data(data):
    """
    Rescales the data to the range [0, 1].

    Parameters:
        data (pandas.Series): The data to rescale.

    Returns:
        pandas.Series: Rescaled data.
    """
    return (data - data.min()) / (data.max() - data.min())

def convert_to_timestamp(time_str, reference_date='2021-09-28'):
    """
    Converts a time string to a timestamp.

    Parameters:
        time_str (str): The time string to convert.
        reference_date (str): The reference date for the conversion.

    Returns:
        int: The corresponding timestamp.
    """
    datetime_str = f"{reference_date} {time_str}"
    datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    timestamp = int(datetime_obj.timestamp())
    return timestamp

def process_timeframes(timeframes):
    """
    Processes timeframes into a list of start and end timestamps.

    Parameters:
        timeframes (list): List of timeframes as strings in the format "start_time - end_time".

    Returns:
        list: List of tuples with start and end timestamps.
    """
    timestamps = []
    for timeframe in timeframes:
        start_time, end_time = timeframe.split(' - ')
        start_timestamp = convert_to_timestamp(start_time)
        end_timestamp = convert_to_timestamp(end_time)
        timestamps.append((start_timestamp, end_timestamp))
    return timestamps

def get_video_metadata(video_dir):
    """
    Retrieves the duration and time reference from the metadata of a video.

    Parameters:
        video_dir (str): Path to the video file.

    Returns:
        tuple: (duration, time_reference) if both values are found in the metadata.
    
    Raises:
        ValueError: If the metadata does not contain the necessary information.
    """
    cmd = [
        'ffmpeg', '-i', video_dir,
        '-f', 'ffmetadata', '-show_entries', 'format=duration:format_tags=time_reference',
        '-v', 'quiet', '-of', 'csv=p=0'
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    output = result.stdout.strip().split(',')
    
    if len(output) == 2:
        duration = float(output[0])
        time_reference = float(output[1])
        return duration, time_reference
    else:
        raise ValueError(f"Can't find metadata in: {video_dir}")

def is_within_timeframes(timestamp, timeframes):
    """
    Checks if a given timestamp falls within any of the specified timeframes.

    Parameters:
        timestamp (float): The timestamp to check.
        timeframes (list): List of tuples containing start and end times.

    Returns:
        bool: True if the timestamp is within any of the timeframes, False otherwise.
    """
    for start_time, end_time in timeframes:
        if start_time <= timestamp <= end_time:
            return True
    return False

def correlate_timestamp_with_video(segments, video_start_time, video_duration, min_duration):
    """
    Correlates the identified segments with the video timeline.

    Parameters:
        segments (list): List of identified segments.
        video_start_time (float): Start time of the video.
        video_duration (float): Duration of the video.
        min_duration (int): Minimum duration for segments to be considered.

    Returns:
        list: List of correlated segments within the video timeline.
    """
    correlated_times = []
    video_end_time = video_start_time + video_duration

    print(f"Correlating segments from {video_start_time} to {video_end_time}")

    for segment in segments:
        start_time, end_time, _ = segment
        
        if end_time <= video_start_time or start_time >= video_end_time:
            continue
        if start_time < video_start_time:
            start_time = video_start_time
        if end_time > video_end_time:
            end_time = video_end_time
        
        duration = end_time - start_time
        if duration >= min_duration:
            correlated_times.append((start_time - video_start_time, end_time - video_start_time))
        else:
            print(f"Segment too short")

    print(f"Correlated times: {correlated_times}")
    return correlated_times

def parse_log_file(file_path):
    """
    Parses a log file to extract steps with timestamps and descriptions.

    Parameters:
        file_path (str): Path to the log file.

    Returns:
        list: A list of parsed steps with start time, end time, description, and timestamp.
    """
    steps = []
    current_step = None
    
    with open(file_path, 'r') as file:
        log_lines = file.readlines()

    for line in log_lines:
        match = re.match(r'\[(\d+)\]\[(\d{2}:\d{2}:\d{2}\.\d{3})\] (.+)', line)
        if match:
            timestamp, time_str, description = match.groups()
            timestamp = int(timestamp)
            time_obj = datetime.strptime(time_str, "%H:%M:%S.%f")

            if current_step:
                current_step['end_time'] = time_obj
                steps.append(current_step)

            current_step = {
                'start_time': time_obj,
                'description': description,
                'timestamp': timestamp
            }

    if current_step:
        steps.append(current_step)

    return steps

def get_log_steps(log_file_path):
    """
    Retrieves log steps and their durations from a parsed log file.

    Parameters:
        log_file_path (str): Path to the log file.

    Returns:
        list: A list of steps with their descriptions, start and end times.
    """
    steps = parse_log_file(log_file_path)
    step_durations = []

    for step in steps:
        start_time = step['start_time']
        end_time = step['end_time'] if 'end_time' in step else None
        description = step['description']
        step_durations.append({
            'description': description,
            'start_time': start_time.strftime('%H:%M:%S.%f'),
            'end_time': end_time.strftime('%H:%M:%S.%f') if end_time else 'Ongoing'
        })

    return step_durations

def group_log_by_steps(log_file_path):
    """
    Groups log entries by their respective steps.

    Parameters:
        log_file_path (str): Path to the log file.

    Returns:
        dict: A dictionary where keys are step labels and values are lists of corresponding log entries.
    """
    steps = parse_log_file(log_file_path)
    grouped_steps = {}
    current_step_label = None

    for step in steps:
        description = step['description']
        if re.match(r'\d+\.\d+ Step\d+:', description):
            current_step_label = description.split(':')[0].strip()

        if current_step_label:
            if current_step_label not in grouped_steps:
                grouped_steps[current_step_label] = []

            grouped_steps[current_step_label].append({
                'description': description,
                'start_time': step['start_time'].strftime('%H:%M:%S.%f'),
                'timestamp': step['timestamp']
            })

    return grouped_steps