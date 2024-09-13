import numpy as np
from datetime import datetime
import re

def is_noisy(data, threshold):
    return np.std(data) > threshold

def smooth_data(data, window_size):
    return data.rolling(window=window_size).mean()

def rescale_data(data):
    return (data - data.min()) / (data.max() - data.min())

def convert_to_timestamp(time_str, reference_date='2021-09-28'):
    datetime_str = f"{reference_date} {time_str}"
    datetime_obj = datetime.strptime(datetime_str, '%Y-%m-%d %H:%M:%S')
    timestamp = int(datetime_obj.timestamp())
    return timestamp

def process_timeframes(timeframes):
    timestamps = []
    for timeframe in timeframes:
        start_time, end_time = timeframe.split(' - ')
        start_timestamp = convert_to_timestamp(start_time)
        end_timestamp = convert_to_timestamp(end_time)
        timestamps.append((start_timestamp, end_timestamp))
    return timestamps

def parse_log_file(file_path):
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