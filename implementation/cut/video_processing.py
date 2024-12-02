import os
import ffmpeg
import logging
from datetime import datetime
from dateutil import parser, tz
import pytz
from ..shared.config import MIN_DURATION, PADDING_SECONDS, OVERLAY_DURATION, FONT_FILE
from ..shared.utils import find_log_step, unix_timestamp_to_seconds_since_midnight, parse_log_file
from ..cut.generate_table import generate_excel_table, collect_segment_info

def get_video_metadata(video_path):
    """
    Retrieves the duration and start timestamp of a video.

    Parameters:
        video_path (str): Path to the video file.

    Returns:
        tuple: (duration, start_timestamp)
    """
    probe = ffmpeg.probe(video_path)
    format_info = probe['format']
    tags = format_info.get('tags', {})
    creation_time_str = tags.get('creation_time')
    if not creation_time_str:
        raise ValueError(f"The 'creation_time' tag is missing in {video_path}")
    creation_time = parser.parse(creation_time_str)
    if creation_time.tzinfo is None:
        creation_time = creation_time.replace(tzinfo=tz.tzutc())
    start_timestamp = creation_time.timestamp()
    duration = float(format_info['duration'])
    return duration, start_timestamp


def group_videos_by_start_time_and_type(video_files, video_dir):
    """
    Groups videos by their start time and type.

    Parameters:
        video_files (list): List of video filenames.
        video_dir (str): Directory containing the video files.

    Returns:
        dict: {start_time: {video_type: [video_files]}}
    """
    grouped_videos = {}
    for video_file in video_files:
        video_path = os.path.join(video_dir, video_file)
        try:
            _, video_start_time = get_video_metadata(video_path)
        except ValueError as e:
            logging.error(e)
            continue

        video_type = extract_video_type(video_file)

        if video_start_time not in grouped_videos:
            grouped_videos[video_start_time] = {}

        if video_type not in grouped_videos[video_start_time]:
            grouped_videos[video_start_time][video_type] = []

        grouped_videos[video_start_time][video_type].append(video_file)

    return grouped_videos


def extract_video_type(filename):
    """
    Extracts the video type from the filename.

    Parameters:
        filename (str): The video file name.

    Returns:
        str: The extracted video type.
    """
    if '-' in filename:
        video_type_part = filename.split('-')[1]
        video_type = video_type_part.split('_compressed')[0]
    else:
        video_type = 'Unknown'
    return video_type

def get_adjacent_video(current_video_file, grouped_videos, video_dir, video_type, direction='next'):
    """
    Gets the adjacent video file in the specified direction for the same video type.

    Parameters:
        current_video_file (str): Current video file name.
        grouped_videos (dict): Videos grouped by start time and type.
        video_dir (str): Directory containing the video files.
        video_type (str): The type of the current video.
        direction (str): 'next' or 'previous'.

    Returns:
        tuple: (adjacent_video_file, start_time, end_time) or None if not found.
    """
    current_video_start_time = None
    for start_time, videos_by_type in grouped_videos.items():
        if video_type in videos_by_type and current_video_file in videos_by_type[video_type]:
            current_video_start_time = start_time
            break

    if current_video_start_time is None:
        return None

    sorted_times = sorted(grouped_videos.keys())
    current_index = sorted_times.index(current_video_start_time)

    if direction == 'next' and current_index < len(sorted_times) - 1:
        adjacent_start_time = sorted_times[current_index + 1]
    elif direction == 'previous' and current_index > 0:
        adjacent_start_time = sorted_times[current_index - 1]
    else:
        return None

    adjacent_videos_by_type = grouped_videos[adjacent_start_time]
    adjacent_video_file = None
    if video_type in adjacent_videos_by_type:
        adjacent_video_file = adjacent_videos_by_type[video_type][0]
    else:
        return None

    video_path = os.path.join(video_dir, adjacent_video_file)
    try:
        video_duration, video_start_time = get_video_metadata(video_path)
    except ValueError as e:
        logging.error(e)
        return None

    video_end_time = video_start_time + video_duration

    return adjacent_video_file, video_start_time, video_end_time


def correlate_timestamp_with_video(segments, video_start_time, video_duration, video_file, grouped_videos, video_dir, video_type):
    """
    Correlates segments with video playback time, considers padding, and includes other videos if necessary.
    Merging logic removed.

    Parameters:
        segments (list): List of segments.
        video_start_time (float): Start time of the current video.
        video_duration (float): Duration of the current video.
        video_file (str): Name of the current video file.
        grouped_videos (dict): Videos grouped by start time and type.
        video_dir (str): Directory containing the video files.
        video_type (str): The type of the current video.

    Returns:
        list: List of segment information.
    """
    correlated_times = []
    video_end_time = video_start_time + video_duration

    for segment in segments:
        start_time, end_time, _ = segment
        los_issue_start_time = start_time
        los_issue_end_time = end_time

        segment_start_time = start_time - PADDING_SECONDS
        segment_end_time = end_time + PADDING_SECONDS
        segment_start_time = max(segment_start_time, video_start_time)
        segment_end_time = min(segment_end_time, video_end_time)

        needs_previous_video = segment_start_time < video_start_time
        needs_next_video = segment_end_time > video_end_time

        video_inputs = [(video_file, video_start_time, video_end_time)]

        if needs_previous_video:
            previous_video_info = get_adjacent_video(video_file, grouped_videos, video_dir, video_type, direction='previous')
            if previous_video_info:
                prev_video_file, prev_start_time, prev_end_time = previous_video_info
                video_inputs.insert(0, (prev_video_file, prev_start_time, prev_end_time))
                segment_start_time = max(segment_start_time, prev_start_time)
            else:
                segment_start_time = video_start_time

        if needs_next_video:
            next_video_info = get_adjacent_video(video_file, grouped_videos, video_dir, video_type, direction='next')
            if next_video_info:
                next_video_file, next_start_time, next_end_time = next_video_info
                video_inputs.append((next_video_file, next_start_time, next_end_time))
                segment_end_time = min(segment_end_time, next_end_time)
            else:
                segment_end_time = video_end_time

        if segment_end_time <= segment_start_time:
            continue
        segment_info = {
            'video_inputs': video_inputs,
            'segment_start_time': segment_start_time,
            'segment_end_time': segment_end_time,
            'los_issue_start_time': los_issue_start_time,
            'los_issue_end_time': los_issue_end_time,
            'video_type': video_type
        }
        correlated_times.append(segment_info)

    return correlated_times

def cut_video_segments(
    segments,
    phantom_missing,
    video_dir,
    results_dir,
    trial_number,
    LOG_FILE,
    VIDEO_FILES,
    pretrial,
    trial_type
):
    """
    Cuts video segments from given videos and adds overlays.

    Parameters:
        segments (list): List of segments.
        phantom_missing (list): List of phantom missing segments.
        video_dir (str): Directory containing the video files.
        results_dir (str): Directory for the output of the cut videos.
        trial_number (str): The trial number extracted from the directory name.
        LOG_FILE (str): The concatenated log file content.
        VIDEO_FILES (list): List of video files for the current trial.
        pretrial (bool): Indicates if it's a pretrial.
        trial_type (str): The trial type extracted from the directory name.
    """
    if LOG_FILE and not pretrial:
        log_steps = parse_log_file(LOG_FILE)
    else:
        logging.warning("No log file found or pretrial data. Skipping log step annotations.")
        log_steps = None

    grouped_videos = group_videos_by_start_time_and_type(VIDEO_FILES, video_dir)
    segment_info_list = []

    local_tz = pytz.timezone('Europe/Berlin')

    for start_time, videos_by_type in grouped_videos.items():
        folder_name = datetime.fromtimestamp(start_time, tz=local_tz).strftime('%Y-%m-%d_%H-%M-%S')
        base_output_dir = os.path.join(results_dir, f"Trial_{trial_number}", folder_name)

        for video_type, videos in videos_by_type.items():
            output_dir = os.path.join(base_output_dir, video_type)
            has_valid_segments = False

            for video_file in videos:
                video_path = os.path.join(video_dir, video_file)
                try:
                    video_duration, video_start_time = get_video_metadata(video_path)
                except ValueError as e:
                    logging.error(e)
                    continue

                video_segments = correlate_timestamp_with_video(
                    segments, video_start_time, video_duration, video_file, grouped_videos, video_dir, video_type
                )

                for seg in video_segments:
                    seg['adjusted_start_time'] = seg['segment_start_time'] + PADDING_SECONDS
                    seg['adjusted_end_time'] = seg['segment_end_time'] - PADDING_SECONDS

                    seg['adjusted_start_time'] = max(seg['adjusted_start_time'], seg['segment_start_time'])
                    seg['adjusted_end_time'] = min(seg['adjusted_end_time'], seg['segment_end_time'])

                    seg['adjusted_duration'] = seg['adjusted_end_time'] - seg['adjusted_start_time']

                video_segments = [
                    seg for seg in video_segments
                    if seg['adjusted_duration'] >= MIN_DURATION
                ]

                if not video_segments:
                    continue

                if not has_valid_segments:
                    os.makedirs(output_dir, exist_ok=True)
                    has_valid_segments = True

                for j, segment_info in enumerate(video_segments):
                    try:
                        los_issue_start_time = segment_info.get(
                            'los_issue_start_time',
                            segment_info['segment_start_time'] + PADDING_SECONDS
                        )
                        los_issue_end_time = segment_info.get(
                            'los_issue_end_time',
                            segment_info['segment_end_time'] - PADDING_SECONDS
                        )

                        actual_padding_start = los_issue_start_time - segment_info['segment_start_time']
                        actual_padding_end = segment_info['segment_end_time'] - los_issue_end_time

                        los_issue_duration = los_issue_end_time - los_issue_start_time

                        segment_duration = segment_info['segment_end_time'] - segment_info['segment_start_time']

                        inputs = []
                        streams = []
                        for _, (vid_file, vid_start, vid_end) in enumerate(segment_info['video_inputs']):
                            vid_path = os.path.join(video_dir, vid_file)
                            ss = max(segment_info['segment_start_time'] - vid_start, 0)
                            duration = min(segment_info['segment_end_time'], vid_end) - max(segment_info['segment_start_time'], vid_start)
                            if duration <= 0:
                                logging.warning(f"Invalid duration for video segment {vid_file}. Skipping.")
                                continue

                            input_video = ffmpeg.input(vid_path, ss=ss, t=duration)
                            inputs.append(input_video)
                            streams.append(input_video)

                        if not streams:
                            logging.warning(f"No valid video streams found for segment {j+1}. Skipping.")
                            continue

                        if len(streams) > 1:
                            video_concat = ffmpeg.concat(*streams, v=1, a=1).node
                            video_stream = video_concat[0]
                            audio_stream = video_concat[1]
                        else:
                            video_stream = streams[0]
                            audio_stream = streams[0].audio

                        video_stream = video_stream.filter('fps', fps=30)

                        if actual_padding_start > 0:
                            overlay_start = actual_padding_start
                            overlay_end = overlay_start + OVERLAY_DURATION
                            video_stream = video_stream.filter(
                                'drawtext',
                                text='LOS Problem start',
                                enable=f'between(t,{overlay_start},{overlay_end})',
                                x='(w-text_w)/2',
                                y='(h-text_h)/2',
                                fontsize=60,
                                fontcolor='white',
                                fontfile=FONT_FILE,
                                box=1,
                                boxcolor='black@0.75',
                                borderw=2,
                                bordercolor='white'
                            )
                        if actual_padding_end > 0:
                            overlay_start = segment_duration - actual_padding_end
                            overlay_end = overlay_start + OVERLAY_DURATION
                            video_stream = video_stream.filter(
                                'drawtext',
                                text='LOS Problem end',
                                enable=f'between(t,{overlay_start},{overlay_end})',
                                x='(w-text_w)/2',
                                y='(h-text_h)/2',
                                fontsize=60,
                                fontcolor='white',
                                fontfile=FONT_FILE,
                                box=1,
                                boxcolor='black@0.75',
                                borderw=2,
                                bordercolor='white'
                            )

                        for phantom_segment in phantom_missing:
                            phantom_start_time = float(phantom_segment[0])
                            phantom_end_time = float(phantom_segment[1])

                            if (phantom_end_time <= segment_info['segment_start_time']) or (phantom_start_time >= segment_info['segment_end_time']):
                                continue
                            overlap_start = max(phantom_start_time, segment_info['segment_start_time'])
                            overlap_end = min(phantom_end_time, segment_info['segment_end_time'])
                            overlay_start_time = overlap_start - segment_info['segment_start_time']
                            overlay_end_time = overlap_end - segment_info['segment_start_time']

                            video_stream = video_stream.filter(
                                'drawtext',
                                text='Phantom transforms missing',
                                enable=f'between(t,{overlay_start_time},{overlay_end_time})',
                                x=10,
                                y='h-text_h-10',
                                fontsize=40,
                                fontcolor='yellow',
                                fontfile=FONT_FILE,
                                box=1,
                                boxcolor='black@0.5',
                                borderw=2,
                                bordercolor='yellow'
                            )

                        formatted_duration = f"{los_issue_duration:.2f}"
                        video_stream = video_stream.filter(
                            'drawtext',
                            text=f'length: {formatted_duration}',
                            x=10,
                            y=10,
                            fontsize=40,
                            fontcolor='white',
                            fontfile=FONT_FILE,
                            box=1,
                            boxcolor='black@0.5',
                            borderw=2,
                            bordercolor='white'
                        )
                        start_time_str = datetime.fromtimestamp(segment_info['segment_start_time'], tz=local_tz).strftime('%H-%M-%S')

                        if log_steps and not pretrial:
                            los_issue_start_time_seconds = unix_timestamp_to_seconds_since_midnight(los_issue_start_time)
                            log_step_description = find_log_step(los_issue_start_time_seconds, log_steps)
                            if log_step_description is None:
                                log_step_label = "NoLogStep"
                            else:
                                log_step_label = log_step_description.replace(" ", "_").replace(":", "-").replace("/", "-")
                        else:
                            log_step_description = ''
                            log_step_label = "NoAnnotations"

                        output_filename = os.path.join(
                            output_dir,
                            f'segment_{j+1}_{start_time_str}_{log_step_label}_{video_type}.mp4'
                        )

                        (
                            ffmpeg
                            .output(video_stream, audio_stream, output_filename, vcodec='libx264', acodec='aac', g=60)
                            .run(quiet=True, overwrite_output=True)
                        )

                        logging.info(f"Created video segment: {output_filename}")

                        segment_info['video_inputs'] = [
                            (vid_file.replace(video_type, '*'), vid_start, vid_end)
                            for vid_file, vid_start, vid_end in segment_info['video_inputs']
                        ]

                        collect_segment_info(
                            segment_info_list,
                            segment_info,
                            los_issue_duration,
                            j,
                            log_steps,
                            log_step_description,
                            los_issue_start_time,
                            trial_number,
                            pretrial,
                            trial_type
                        )

                    except ffmpeg.Error as e:
                        logging.error(f"FFmpeg Error for {output_filename}: {e.stderr.decode()}")
                    except Exception as e:
                        logging.error(f"Unexpected error creating video segment {output_filename}: {e}")

    if segment_info_list:
        excel_output_path = os.path.join(results_dir, 'segment_info.xlsx')
        generate_excel_table(segment_info_list, excel_output_path)
        logging.info(f"Segment information written to Excel file: {excel_output_path}")
    else:
        logging.info("No segment information to write to Excel.")