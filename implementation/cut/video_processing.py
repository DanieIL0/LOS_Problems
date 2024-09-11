import os
import ffmpeg
from datetime import datetime
from ..shared.config import VIDEO_FILES, MIN_DURATION

def get_video_metadata(video_path):
    probe = ffmpeg.probe(video_path)
    format_info = probe['format']
    creation_time_str = format_info['tags']['creation_time']
    creation_time = datetime.fromisoformat(creation_time_str.replace('Z', '+00:00'))
    start_timestamp = creation_time.timestamp()
    duration = float(format_info['duration'])
    return duration, start_timestamp

def correlate_timestamp_with_video(segments, video_start_time, video_duration):
    correlated_times = []
    video_end_time = video_start_time + video_duration

    for segment in segments:
        start_time, end_time, _ = segment
        
        if end_time <= video_start_time or start_time >= video_end_time:
            continue
        
        if start_time < video_start_time:
            start_time = video_start_time
        if end_time > video_end_time:
            end_time = video_end_time
        
        correlated_times.append((start_time - video_start_time, end_time - video_start_time))
        print(f"Correlated segment: Start={start_time - video_start_time}, End={end_time - video_start_time}")

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

        video_segments = correlate_timestamp_with_video(segments, video_start_time, video_duration)

        video_segments = [seg for seg in video_segments if seg[1] - seg[0] >= MIN_DURATION]

        for j, (start, end) in enumerate(video_segments):
            output_filename = os.path.join(results_dir, f'cut_segment_{j+1}.mp4')

            try:
                (
                    ffmpeg
                    .input(video_path, ss=start, to=end)
                    .output(output_filename, vcodec='copy', acodec='copy')
                    .run(quiet=True, overwrite_output=True)
                )
                print(f"Created video segment: {output_filename}")
            except Exception as e:
                print(f"Error creating video segment {output_filename}: {e}")