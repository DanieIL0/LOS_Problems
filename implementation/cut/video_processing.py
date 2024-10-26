import os
import ffmpeg
import logging
from datetime import datetime
from dateutil.parser import parse
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
    creation_time = parse(creation_time_str)
    start_timestamp = creation_time.timestamp()
    duration = float(format_info['duration'])
    return duration, start_timestamp


def group_videos_by_start_time(video_files, video_dir):
    """
    Groups videos by their start timestamp.

    Parameters:
        video_files (list): List of video filenames.
        video_dir (str): Directory containing the video files.

    Returns:
        dict: Videos grouped by start timestamp.
    """
    grouped_videos = {}
    
    for video_file in video_files:
        video_path = os.path.join(video_dir, video_file)
        try:
            _, video_start_time = get_video_metadata(video_path)
        except ValueError as e:
            logging.error(e)
            continue

        video_start_time = int(video_start_time)
        if video_start_time not in grouped_videos:
            grouped_videos[video_start_time] = []
        
        grouped_videos[video_start_time].append(video_file)
    
    return grouped_videos

def get_adjacent_video(current_video_file, grouped_videos, video_dir, direction='next'):
    """
    Finds the previous or next video based on the start timestamp.

    Parameters:
        current_video_file (str): Name of the current video file.
        grouped_videos (dict): Dictionary of grouped videos.
        video_dir (str): Directory containing the video files.
        direction (str): 'previous' or 'next'.

    Returns:
        tuple or None: Tuple with (video_file, start_time, end_time) or None.
    """
    video_times = sorted(grouped_videos.keys())
    current_video_time = None
    for time, videos in grouped_videos.items():
        if current_video_file in videos:
            current_video_time = time
            break

    if current_video_time is None:
        return None

    index = video_times.index(current_video_time)
    if direction == 'previous' and index > 0:
        prev_time = video_times[index - 1]
        prev_video_file = grouped_videos[prev_time][0]
        prev_video_path = os.path.join(video_dir, prev_video_file)
        prev_duration, prev_start_time = get_video_metadata(prev_video_path)
        prev_end_time = prev_start_time + prev_duration
        return prev_video_file, prev_start_time, prev_end_time
    elif direction == 'next' and index < len(video_times) - 1:
        next_time = video_times[index + 1]
        next_video_file = grouped_videos[next_time][0]
        next_video_path = os.path.join(video_dir, next_video_file)
        next_duration, next_start_time = get_video_metadata(next_video_path)
        next_end_time = next_start_time + next_duration
        return next_video_file, next_start_time, next_end_time
    else:
        return None

def correlate_timestamp_with_video(segments, video_start_time, video_duration, video_file, grouped_videos, video_dir):
    """
    Correlates segments with video playback time, considers padding, and includes other videos if necessary.

    Parameters:
        segments (list): List of segments.
        video_start_time (float): Start time of the current video.
        video_duration (float): Duration of the current video.
        video_file (str): Name of the current video file.
        grouped_videos (dict): Videos grouped by start time.
        video_dir (str): Directory containing the video files.

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
            previous_video_info = get_adjacent_video(video_file, grouped_videos, video_dir, direction='previous')
            if previous_video_info:
                prev_video_file, prev_start_time, prev_end_time = previous_video_info
                video_inputs.insert(0, (prev_video_file, prev_start_time, prev_end_time))
                segment_start_time = max(segment_start_time, prev_start_time)
            else:
                segment_start_time = video_start_time

        if needs_next_video:
            next_video_info = get_adjacent_video(video_file, grouped_videos, video_dir, direction='next')
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
            'los_issue_end_time': los_issue_end_time
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

    grouped_videos = group_videos_by_start_time(VIDEO_FILES, video_dir)
    segment_info_list = []

    for start_time, videos in grouped_videos.items():
        folder_name = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = os.path.join(results_dir, f"Trial_{trial_number}", folder_name)

        has_valid_segments = False

        for video_file in videos:
            video_path = os.path.join(video_dir, video_file)
            try:
                video_duration, video_start_time = get_video_metadata(video_path)
            except ValueError as e:
                logging.error(e)
                continue

            video_segments = correlate_timestamp_with_video(
                segments, video_start_time, video_duration, video_file, grouped_videos, video_dir
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
                    start_time_str = datetime.fromtimestamp(segment_info['segment_start_time']).strftime('%H-%M-%S')

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
                        f'segment_{j+1}_{start_time_str}_{log_step_label}.mp4'
                    )

                    (
                        ffmpeg
                        .output(video_stream, audio_stream, output_filename, vcodec='libx264', acodec='aac', g=60)
                        .run(quiet=True, overwrite_output=True)
                    )

                    logging.info(f"Created video segment: {output_filename}")

                    segment_info['video_inputs'] = [
                        (vid_file.replace('Room', '*'), vid_start, vid_end)
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