import os
import ffmpeg
import logging
from datetime import datetime
from dateutil.parser import parse
import re
from ..shared.config import VIDEO_FILES, MIN_DURATION, PADDING_SECONDS, OVERLAY_DURATION, FONT_FILE, LOG_FILE_DIR
from ..shared.utils import find_log_step, unix_timestamp_to_seconds_since_midnight, parse_log_file

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

def get_video_resolution(video_path):
    """
    Retrieves the resolution of a video.

    Parameters:
        video_path (str): Path to the video file.

    Returns:
        tuple: (width, height)
    """
    probe = ffmpeg.probe(video_path)
    video_streams = [stream for stream in probe['streams'] if stream['codec_type'] == 'video']
    if not video_streams:
        raise ValueError(f"No video streams found in {video_path}")
    width = int(video_streams[0]['width'])
    height = int(video_streams[0]['height'])
    return width, height

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
        original_start_time = start_time
        original_end_time = end_time

        if end_time <= video_start_time or start_time >= video_end_time:
            continue
        adjusted_start_time = start_time - PADDING_SECONDS
        adjusted_end_time = end_time + PADDING_SECONDS
        needs_previous_video = adjusted_start_time < video_start_time
        needs_next_video = adjusted_end_time > video_end_time
        video_inputs = [(video_file, video_start_time, video_end_time)]
        if needs_previous_video:
            previous_video_info = get_adjacent_video(video_file, grouped_videos, video_dir, direction='previous')
            if previous_video_info:
                prev_video_file, prev_start_time, prev_end_time = previous_video_info
                video_inputs.insert(0, (prev_video_file, prev_start_time, prev_end_time))
                adjusted_start_time = max(adjusted_start_time, prev_start_time)
            else:
                adjusted_start_time = video_start_time 

        if needs_next_video:
            next_video_info = get_adjacent_video(video_file, grouped_videos, video_dir, direction='next')
            if next_video_info:
                next_video_file, next_start_time, next_end_time = next_video_info
                video_inputs.append((next_video_file, next_start_time, next_end_time))
                adjusted_end_time = min(adjusted_end_time, next_end_time)
            else:
                adjusted_end_time = video_end_time

        segment_info = {
            'video_inputs': video_inputs,
            'start_time': adjusted_start_time,
            'end_time': adjusted_end_time,
            'original_start_time': original_start_time,
            'original_end_time': original_end_time
        }
        correlated_times.append(segment_info)

    return correlated_times

def cut_video_segments(segments, phantom_missing, video_dir, results_dir):
    """
    Cuts video segments from given videos and adds overlays.

    Parameters:
        segments (list): List of segments.
        phantom_missing (list): List of phantom missing segments.
        video_dir (str): Directory containing the video files.
        results_dir (str): Directory for the output of the cut videos.
    """
    if LOG_FILE_DIR:
        log_steps = parse_log_file(LOG_FILE_DIR)
    else:
        logging.warning("No log file found. Skipping log step annotations.")
        log_steps = None

    grouped_videos = group_videos_by_start_time(VIDEO_FILES, video_dir)

    for start_time, videos in grouped_videos.items():
        folder_name = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = os.path.join(results_dir, folder_name)
        os.makedirs(output_dir, exist_ok=True)

        for video_file in videos:
            video_path = os.path.join(video_dir, video_file)
            try:
                video_duration, video_start_time = get_video_metadata(video_path)
                width, height = get_video_resolution(video_path)
            except ValueError as e:
                logging.error(e)
                continue

            video_segments = correlate_timestamp_with_video(
                segments, video_start_time, video_duration, video_file, grouped_videos, video_dir
            )

            video_segments = [seg for seg in video_segments if seg['end_time'] - seg['start_time'] >= MIN_DURATION]

            for j, segment_info in enumerate(video_segments):
                try:
                    original_start_time = segment_info.get('original_start_time', segment_info['start_time'] + PADDING_SECONDS)
                    original_end_time = segment_info.get('original_end_time', segment_info['end_time'] - PADDING_SECONDS)

                    actual_padding_start = original_start_time - segment_info['start_time']
                    actual_padding_end = segment_info['end_time'] - original_end_time

                    segment_duration = segment_info['end_time'] - segment_info['start_time']

                    inputs = []
                    streams = []
                    for idx, (vid_file, vid_start, vid_end) in enumerate(segment_info['video_inputs']):
                        vid_path = os.path.join(video_dir, vid_file)
                        ss = max(segment_info['start_time'] - vid_start, 0)
                        to = min(segment_info['end_time'] - vid_start, vid_end - vid_start)
                        input_video = ffmpeg.input(vid_path, ss=ss, to=to)
                        inputs.append(input_video)
                        streams.append(input_video)

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

                    # Overlay "Phantom transforms missing" when the timeframe overlaps with phantom_missing segments
                    for phantom_segment in phantom_missing:
                        phantom_start_time = float(phantom_segment[0])
                        phantom_end_time = float(phantom_segment[1])

                        # Check if phantom_segment overlaps with current video segment
                        if (phantom_end_time <= segment_info['start_time']) or (phantom_start_time >= segment_info['end_time']):
                            continue
                        overlap_start = max(phantom_start_time, segment_info['start_time'])
                        overlap_end = min(phantom_end_time, segment_info['end_time'])
                        overlay_start_time = overlap_start - segment_info['start_time']
                        overlay_end_time = overlap_end - segment_info['start_time']

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

                    start_time_str = datetime.fromtimestamp(original_start_time).strftime('%H-%M-%S')

                    if log_steps:
                        original_start_time_seconds = unix_timestamp_to_seconds_since_midnight(original_start_time)

                        log_step_description = find_log_step(original_start_time_seconds, log_steps)
                        if log_step_description is None:
                            log_step_label = "NoLogStep"
                        else:
                            match = re.search(r"Step(\d+)", log_step_description)
                            if match:
                                log_step_label = f"Step{match.group(1)}"
                            else:
                                log_step_label = "UnknownStep"
                    else:
                        log_step_label = "NoLogFile"
                    base_filename = os.path.splitext(video_file)[0]
                    output_filename = os.path.join(
                        output_dir,
                        f'{base_filename}_segment_{j+1}_{start_time_str}_logstep_{log_step_label}.mp4'
                    )

                    (
                        ffmpeg
                        .output(video_stream, audio_stream, output_filename, vcodec='libx264', acodec='aac', g=60)
                        .run(quiet=True, overwrite_output=True)
                    )

                    logging.info(f"Created video segment: {output_filename}")
                except ffmpeg.Error as e:
                    logging.error(f"FFmpeg Error for {output_filename}: {e.stderr.decode()}")
                except Exception as e:
                    logging.error(f"Unexpected error creating video segment {output_filename}: {e}")