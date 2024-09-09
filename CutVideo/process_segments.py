import os
import subprocess
from config import WINDOW_SIZE, THRESHOLD_PERCENTAGE, MIN_DURATION, VIDEO_FILES
from moviepy.video.io.ffmpeg_tools import ffmpeg_extract_subclip

def get_video_metadata(video_path):
    cmd = [
        'ffmpeg', '-i', video_path,
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
        raise ValueError(f"Can't find metadata in: {video_path}")

def process_missing_transformations(timestamps, transformation_data):
    segments = []
    start_timestamp = None

    for i in range(len(transformation_data)):
        # Using rolling window for better results
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

    # Handle case where last segment extends to the end of the data
    if start_timestamp is not None:
        end_timestamp = timestamps[-1]
        segments.append((start_timestamp, end_timestamp))

    return segments

def correlate_timestamp_with_video(segments, video_start_time, video_duration):
    correlated_times = []
    video_end_time = video_start_time + video_duration

    print(f"Correlating segments at {video_start_time} to {video_end_time}")

    for segment in segments:
        start_time, end_time, _ = segment
        
        if end_time <= video_start_time or start_time >= video_end_time:
            continue
        if start_time < video_start_time:
            start_time = video_start_time
        if end_time > video_end_time:
            end_time = video_end_time
        
        duration = end_time - start_time
        if duration >= MIN_DURATION:
            correlated_times.append((start_time - video_start_time, end_time - video_start_time))
        else:
            print(f"Segment too short")

    print(f"Correlated times: {correlated_times}")
    return correlated_times

def cut_video_segments(segments, video_dir, results_dir):
    for video_file in VIDEO_FILES:
        video_path = os.path.join(video_dir, video_file)
        
        try:
            video_duration, video_start_time = get_video_metadata(video_path)
        except ValueError as e:
            print(e)
            continue

        print(f"Processing video: {video_file}")

        video_segments = correlate_timestamp_with_video(segments, video_start_time, video_duration)

        for j, (start, end) in enumerate(video_segments):
            output_filename = os.path.join(results_dir, f'cut_segment_{j+1}.mp4')

            if end - start > MIN_DURATION: 
                try:
                    ffmpeg_extract_subclip(video_path, start, end, targetname=output_filename)
                except Exception as e:
                    print(f"Error creating video {output_filename}: {e}")