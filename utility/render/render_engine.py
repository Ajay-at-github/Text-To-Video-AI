import time
import os
import tempfile
import zipfile
import platform
import subprocess
from moviepy.editor import (AudioFileClip, CompositeVideoClip, CompositeAudioClip, ImageClip,
                            TextClip, VideoFileClip)
from moviepy.audio.fx.audio_loop import audio_loop
from moviepy.audio.fx.audio_normalize import audio_normalize
from moviepy.video.tools.subtitles import SubtitlesClip
import requests

def download_file(url, filename):
    with open(filename, 'wb') as f:
        response = requests.get(url)
        f.write(response.content)

def search_program(program_name):
    try: 
        search_cmd = "where" if platform.system() == "Windows" else "which"
        return subprocess.check_output([search_cmd, program_name]).decode().strip()
    except subprocess.CalledProcessError:
        return None

def get_program_path(program_name):
    program_path = search_program(program_name)
    return program_path

def get_output_media(audio_file_path, timed_captions, background_video_data, video_server):
    OUTPUT_FILE_NAME = "rendered_video.mp4"
    magick_path = get_program_path("magick")
    print(magick_path)
    if magick_path:
        os.environ['IMAGEMAGICK_BINARY'] = magick_path
    else:
        os.environ['IMAGEMAGICK_BINARY'] = '/usr/bin/convert'

    visual_clips = []
    for (t1, t2), video_url in background_video_data:
        try:
            # Download the video file
            video_filename = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name 
            download_file(video_url, video_filename)

            # Create VideoFileClip from the downloaded file
            video_clip = VideoFileClip(video_filename)
            video_clip = video_clip.subclip(t1, t2)  # Use subclip for efficiency
            visual_clips.append(video_clip)

        except Exception as e:
            print(f"Error processing video from {video_url}: {e}")
            # Handle the error, e.g., skip this video, use a fallback, etc.

    audio_clips = []
    audio_file_clip = AudioFileClip(audio_file_path)
    audio_clips.append(audio_file_clip)

    for (t1, t2), text in timed_captions:
        text_clip = TextClip(txt=text, fontsize=100, color="white", stroke_width=3, 
                             stroke_color="black", method="label")
        text_clip = text_clip.set_start(t1)
        text_clip = text_clip.set_end(t2)
        text_clip = text_clip.set_position(["center", 800])
        visual_clips.append(text_clip)

    video = CompositeVideoClip(visual_clips)

    if audio_clips:
        audio = CompositeAudioClip(audio_clips)
        video.duration = audio.duration
        video.audio = audio

    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')

    # Clean up downloaded files
    for (t1, t2), video_url in background_video_data:
        video_filename = tempfile.NamedTemporaryFile(delete=False, suffix=".mp4").name
        try:
            os.remove(video_filename)
        except Exception as e:
            print(f"Error deleting file {video_filename}: {e}")

    return OUTPUT_FILE_NAME
