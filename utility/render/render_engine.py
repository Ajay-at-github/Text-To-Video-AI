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
from requests.exceptions import RequestException
from moviepy.video.tools.subtitles import SubtitlesClip
import requests

import requests
import time
from requests.exceptions import RequestException

def download_file(url, filename, retries=3):
    """Downloads a file from a URL with retry mechanism."""

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }  # Example User-Agent
  
    for _ in range(retries):
        try:
            with open(filename, 'wb') as f:
                response = requests.get(url, stream=True)
                response.raise_for_status()  # Raise an exception for bad status codes

                total_length = response.headers.get('content-length')
                if total_length is None:
                    f.write(response.content)
                else:
                    dl = 0
                    total_length = int(total_length)
                    for data in response.iter_content(chunk_size=4096):
                        dl += len(data)
                        f.write(data)
                        done = int(50 * dl / total_length)
                        print(f"\rDownloading: [{'=' * done}{' ' * (50-done)}] {dl}/{total_length}", end="")
                    print()
            return  # Download successful, exit the loop

        except RequestException as e:
            print(f"Error downloading {url}: {e}")
            # You can add a delay here before retrying
            time.sleep(1)

    print(f"Failed to download {url} after {retries} retries.")
    # You might want to raise an exception or handle the failure in another way

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
            with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as temp_video_file:
                video_filename = temp_video_file.name
                download_file(video_url, video_filename)

                video_clip = VideoFileClip(video_filename)
                video_clip = video_clip.subclip(t1, t2)

                # Resize video clips to a consistent size
                video_clip = video_clip.resize(width=1920)  # Example width, adjust as needed

                visual_clips.append(video_clip)

        except Exception as e:
            print(f"Error processing video from {video_url}: {e}")

    audio_clips = []
    audio_file_clip = AudioFileClip(audio_file_path)
    audio_clips.append(audio_file_clip)

    # Create a separate list for text clips
    text_clips = []
    for (t1, t2), text in timed_captions:
        text_clip = TextClip(txt=text, fontsize=70, color="white", stroke_width=3,
                             stroke_color="black", method="label", font="Arial")  # Specify font
        text_clip = text_clip.set_start(t1)
        text_clip = text_clip.set_end(t2)
        text_clip = text_clip.set_position(("center", "bottom"))  # Position at the bottom
        text_clips.append(text_clip)

    # Composite video clips first
    video = CompositeVideoClip(visual_clips)

    # Overlay text clips on the video
    video = CompositeVideoClip([video] + text_clips)  

    if audio_clips:
        audio = CompositeAudioClip(audio_clips)
        video.duration = audio.duration
        video.audio = audio

    video.write_videofile(OUTPUT_FILE_NAME, codec='libx264', audio_codec='aac', fps=25, preset='veryfast')

    return OUTPUT_FILE_NAME
