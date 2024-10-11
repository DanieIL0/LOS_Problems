import pandas as pd
import openpyxl
from datetime import datetime

def collect_segment_info(
    segment_info_list,
    segment_info,
    los_issue_duration,
    video_file,
    segment_index,
    log_steps,
    log_step_description,
    los_issue_start_time
):
    """
    Collects information about a video segment and appends it to the segment_info_list.

    Parameters:
        segment_info_list (list): List to store segment information dictionaries.
        segment_info (dict): Information about the current segment.
        los_issue_duration (float): Duration of the LOS issue.
        video_file (str): Original video file name.
        segment_index (int): Index of the segment.
        log_steps (list): List of parsed log steps.
        log_step_description (str): Description of the log step.
        los_issue_start_time (float): Start time of the LOS issue.
    """
    # Extract video input details
    origin_videos_info = []
    for vid_file, vid_start, vid_end in segment_info['video_inputs']:
        origin_videos_info.append({
            'vid_file': vid_file,
            'vid_start': vid_start,
            'vid_end': vid_end
        })

    origin_videos = [info['vid_file'] for info in origin_videos_info]
    origin_videos_str = '+'.join(origin_videos)

    vid_starts = [datetime.fromtimestamp(info['vid_start']).strftime('%H:%M:%S') for info in origin_videos_info]
    vid_starts_str = '+'.join(vid_starts)
    vid_ends = [datetime.fromtimestamp(info['vid_end']).strftime('%H:%M:%S') for info in origin_videos_info]
    vid_ends_str = '+'.join(vid_ends)

    segment_number = segment_index + 1

    segment_start_datetime = datetime.fromtimestamp(segment_info['segment_start_time'])
    day = segment_start_datetime.strftime('%d/%m/%Y')
    start_time_cet = segment_start_datetime.strftime('%H:%M:%S')

    length_secs = los_issue_duration

    performed_step = log_step_description if log_step_description else 'NaN'

    if log_steps and log_step_description:
        for step in log_steps:
            if step['description'] == log_step_description:
                step_length_secs = step['end_time'] - step['start_time']
                minutes = int(step_length_secs // 60)
                seconds = int(step_length_secs % 60)
                step_length_mmss = f"{minutes}:{seconds:02d}"
                break
        else:
            step_length_mmss = 'NaN'
    else:
        step_length_mmss = 'NaN'

    # Format los_issue_start_time
    los_issue_start_time_str = datetime.fromtimestamp(los_issue_start_time).strftime('%H:%M:%S')

    # Append the collected data to the list
    segment_info_list.append({
        'Origin Video': origin_videos_str,
        'Video Start Time(s)': vid_starts_str,
        'Video End Time(s)': vid_ends_str,
        'Segment': segment_number,
        'Day': day,
        'Start Time (CET)': start_time_cet,
        'LOS Issue Start Time': los_issue_start_time_str,
        'Length (secs)': f"{length_secs:.2f}",
        'Performed Step': performed_step,
        'Length of step (mm:ss)': step_length_mmss,
        'Reason': ''  # Placeholder,
    })


def generate_excel_table(segment_info_list, excel_output_path):
    """
    Generates an Excel table from the segment information list.

    Parameters:
        segment_info_list (list): List of dictionaries containing segment information.
        excel_output_path (str): Path where the Excel file will be saved.
    """
    df = pd.DataFrame(segment_info_list)
    df.to_excel(excel_output_path, index=False)
