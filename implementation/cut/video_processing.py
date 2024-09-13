import os
import ffmpeg
from datetime import datetime
from ..shared.config import VIDEO_FILES, MIN_DURATION, PADDING_SECONDS, PHANTOM_THRESHOLD

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

def group_videos_by_start_time(video_files, video_dir):
    grouped_videos = {}
    
    for video_file in video_files:
        video_path = os.path.join(video_dir, video_file)
        try:
            _, video_start_time = get_video_metadata(video_path)
        except ValueError as e:
            print(e)
            continue

        if video_start_time not in grouped_videos:
            grouped_videos[video_start_time] = []
        
        grouped_videos[video_start_time].append(video_file)
    
    return grouped_videos

def cut_video_segments(segments, video_dir, results_dir):
    grouped_videos = group_videos_by_start_time(VIDEO_FILES, video_dir)
    
    for start_time, videos in grouped_videos.items():
        folder_name = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d_%H-%M-%S')
        output_dir = os.path.join(results_dir, folder_name)
        os.makedirs(output_dir, exist_ok=True)
        
        for video_file in videos:
            video_path = os.path.join(video_dir, video_file)
            try:
                video_duration, video_start_time = get_video_metadata(video_path)
            except ValueError as e:
                print(e)
                continue

            video_segments = correlate_timestamp_with_video(segments, video_start_time, video_duration)

            video_segments = [seg for seg in video_segments if seg[1] - seg[0] >= MIN_DURATION]

            for j, (start, end) in enumerate(video_segments):
                output_filename = os.path.join(output_dir, f'{video_file}_segment_{j+1}.mp4')

                try:
                    (
                        ffmpeg
                        .input(video_path, ss=start, to=end)
                        .output(
                            output_filename,
                            vcodec='libx264',  
                            acodec='aac',     
                            vf='fps=30',
                            g=60,
                            force_key_frames='expr:gte(t,n_forced*2)'
                        )
                        .run(quiet=True, overwrite_output=True)
                    )
                    print(f"Created video segment: {output_filename}")
                except Exception as e:
                    print(f"Error creating video segment {output_filename}: {e}")