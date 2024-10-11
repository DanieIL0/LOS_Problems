from openpyxl import load_workbook
from datetime import datetime
import pandas as pd

def collect_segment_info(
    segment_info_list,
    segment_info,
    los_issue_duration,
    _,
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
    origin_videos_info = []
    for vid_file, vid_start, vid_end in segment_info['video_inputs']:
        origin_videos_info.append({
            'vid_file': vid_file,
            'vid_start': vid_start,
            'vid_end': vid_end
        })

    origin_videos = [info['vid_file'] for info in origin_videos_info]
    origin_videos_str = '+'.join(origin_videos)

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

    los_issue_start_time_str = datetime.fromtimestamp(los_issue_start_time).strftime('%H:%M:%S')

    segment_info_list.append({
        'Origin Video': origin_videos_str,
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
    df.to_excel(excel_output_path, index=False, engine='openpyxl')

    wb = load_workbook(excel_output_path)
    ws = wb.active

    column_letters = {}
    for cell in ws[1]:
        column_letters[cell.value] = cell.column_letter

    if 'Origin Video' in column_letters:
        origin_video_column = column_letters['Origin Video']
        current_width = ws.column_dimensions[origin_video_column].width
        if current_width is None:
            current_width = 8
        ws.column_dimensions[origin_video_column].width = 52

    if 'Reason' in column_letters:
        reason_column = column_letters['Reason']
        current_width = ws.column_dimensions[reason_column].width
        if current_width is None:
            current_width = 8
        ws.column_dimensions[reason_column].width = 60

    if 'Performed Step' in column_letters:
        performed_step_column = column_letters['Performed Step']
        current_width = ws.column_dimensions[performed_step_column].width
        if current_width is None:
            current_width = 8
        ws.column_dimensions[performed_step_column].width = 45

    wb.save(excel_output_path)