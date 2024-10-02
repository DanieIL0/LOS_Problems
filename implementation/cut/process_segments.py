import os
import logging
from ..shared.config import WINDOW_SIZE, THRESHOLD_PERCENTAGE, MIN_DURATION, VIDEO_FILES
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip
from ..shared.utils import get_video_metadata, correlate_timestamp_with_video

def process_missing_transformations(timestamps, transformation_data):
    """
    Processes missing transformations and identifies segments where the threshold is exceeded.

    Parameters:
        timestamps (list): List of timestamps corresponding to the transformation data.
        transformation_data (list): List of transformation data where missing transformations are marked as zero.

    Returns:
        list: Segments where the missing transformations exceed the threshold.
    """
    segments = []
    start_timestamp = None

    for i in range(len(transformation_data)):
        # Using a rolling window to smooth data
        window_start = max(0, i - WINDOW_SIZE + 1)
        window_data = transformation_data[window_start:i + 1]
        missing_count = window_data.count(0)

        if missing_count >= THRESHOLD_PERCENTAGE:
            if start_timestamp is None:
                start_timestamp = timestamps[window_start]
        else:
            if start_timestamp is not None:
                end_timestamp = timestamps[i - 1]
                segments.append((start_timestamp, end_timestamp))
                start_timestamp = None

    # Handle case where the last segment extends to the end
    if start_timestamp is not None:
        end_timestamp = timestamps[-1]
        segments.append((start_timestamp, end_timestamp))

    return segments

def cut_video_segments(segments, video_dir, results_dir):
    """
    Cuts the video segments based on the correlated segments and saves them.

    Parameters:
        segments (list): List of correlated segments.
        video_dir (str): Directory containing the video files.
        results_dir (str): Directory where the cut segments will be saved.
    """
    for video_file in VIDEO_FILES:
        video_path = os.path.join(video_dir, video_file)
        
        try:
            video_duration, video_start_time = get_video_metadata(video_path)
        except ValueError as e:
            logging.error(e)
            continue

        logging.info(f"Processing video: {video_file}")

        video_segments = correlate_timestamp_with_video(segments, video_start_time, video_duration, MIN_DURATION)

        for j, (start, end) in enumerate(video_segments):
            output_filename = os.path.join(results_dir, f'cut_segment_{j+1}.mp4')

            if end - start > MIN_DURATION: 
                try:
                    ffmpeg_extract_subclip(video_path, start, end, targetname=output_filename)
                except Exception as e:
                    logging.error(f"Error creating video {output_filename}: {e}")